module ForemanNutanix
  class GCE < ComputeResource
    validates :cluster, presence: true

    def self.provider_friendly_name
      'Nutanix'
    end

    def self.available?
      true
    end

    def capabilities
      [:build]
    end

    def cluster=(cluster)
      self.url = cluster
    end

    def cluster
      url
    end

    def to_label
      "#{name} (#{provider_friendly_name})"
    end

    def provided_attributes
      super.merge({ ip: :vm_ip_address })
    end

    # Test connection to the compute resource
    def test_connection(options = {})
      Rails.logger.info "=== NUTANIX: Testing connection to cluster #{cluster} ==="
      true
    end

    # Available clusters for selection
    def available_clusters
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/clustermgmt/list-clusters")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      data.map do |cluster|
        cluster[:name] = "#{cluster['name']} (#{cluster['arch']})"
        OpenStruct.new(cluster)
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error fetching clusters: #{e.message} ==="
      []
    end

    # Available networks for VMs
    def available_networks(_cluster_id = nil)
      Rails.logger.info "=== NUTANIX: Returning available networks ==="
      [OpenStruct.new({ id: 'default-network', name: 'Default Network' })]
    end

    # Networks method (alias for available_networks)
    def networks(opts = {})
      Rails.logger.info "=== NUTANIX: NETWORKS called with opts: #{opts} ==="
      available_networks
    end

    # Available machine types/flavors
    def available_flavors
      Rails.logger.info "=== NUTANIX: Returning available flavors ==="
      [OpenStruct.new({ id: 'small', name: 'Small (2 CPU, 4GB RAM)' })]
    end
    alias_method :machine_types, :available_flavors

    # Available images
    def available_images(_opts = {})
      Rails.logger.info "=== NUTANIX: Returning available images ==="
      [OpenStruct.new({ id: 'centos-7', name: 'CentOS 7' })]
    end

    # Core provisioning method - this is what Foreman calls to create a VM
    def create_vm(args = {})
      Rails.logger.info "=== NUTANIX: CREATE_VM CALLED with args: #{args} ==="
      Rails.logger.info "=== NUTANIX: CREATE_VM caller: #{caller_locations(1,3).join(', ')} ==="
      
      vm = new_vm(args)
      Rails.logger.info "=== NUTANIX: CREATE_VM calling vm.save ==="
      vm.save
      
      Rails.logger.info "=== NUTANIX: CREATE_VM returning VM: #{vm} ==="
      find_vm_by_uuid(vm.identity)
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: CREATE_VM ERROR: #{e.message} ==="
      raise e
    end

    # New VM instance (not persisted)
    def new_vm(attr = {})
      Rails.logger.info "=== NUTANIX: NEW_VM CALLED with attr: #{attr} ==="
      vm_attrs = vm_instance_defaults.merge(attr.to_hash.deep_symbolize_keys)
      Rails.logger.info "=== NUTANIX: NEW_VM merged attrs: #{vm_attrs} ==="
      
      # Use the Foreman pattern - client.servers.new returns our VM model
      client.servers.new(vm_attrs)
    end

    # Default attributes for new VMs
    def vm_instance_defaults
      Rails.logger.info "=== NUTANIX: VM_INSTANCE_DEFAULTS called ==="
      {
        zone: 'default-zone',
        machine_type: 'small'
      }
    end

    # Find existing VM by UUID
    def find_vm_by_uuid(uuid)
      Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID CALLED with uuid: #{uuid} ==="
      vm = NutanixCompute.new(cluster, { name: uuid, identity: uuid })
      vm.instance_variable_set(:@persisted, true) # Mark as persisted since we're "finding" it
      Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID returning VM: #{vm} ==="
      vm
    end

    # Foreman might call ready? on the compute resource
    def ready?
      Rails.logger.info "=== NUTANIX: GCE::ready? called ==="
      true
    end

    # Destroy VM
    def destroy_vm(uuid)
      Rails.logger.info "=== NUTANIX: DESTROY_VM CALLED with uuid: #{uuid} ==="
      true
    rescue ActiveRecord::RecordNotFound
      true
    end

    # Console access
    def console(uuid)
      Rails.logger.info "=== NUTANIX: CONSOLE CALLED with uuid: #{uuid} ==="
      vm = find_vm_by_uuid(uuid)
      {
        'output' => 'Mock console output', 'timestamp' => Time.now.utc,
        :type => 'log', :name => vm.name
      }
    end

    # Associate host with VM
    def associated_host(vm)
      Rails.logger.info "=== NUTANIX: ASSOCIATED_HOST CALLED for vm: #{vm.name} ==="
      associate_by('ip', [vm.vm_ip_address, vm.private_ip_address])
    end

    # User data support
    def user_data_supported?
      true
    end

    # New volume creation
    def new_volume(attrs = {})
      Rails.logger.info "=== NUTANIX: NEW_VOLUME CALLED with attrs: #{attrs} ==="
      OpenStruct.new(attrs)
    end

    # Host attributes for VM creation
    def host_create_attrs(host)
      Rails.logger.info "=== NUTANIX: HOST_CREATE_ATTRS CALLED for host: #{host.name} ==="
      super
    end

    # Validate host before provisioning
    def validate_host(host)
      Rails.logger.info "=== NUTANIX: VALIDATE_HOST CALLED for host: #{host.name} ==="
      super
    end

    private

    def client
      Rails.logger.info "=== NUTANIX: Creating client for cluster #{cluster} ==="
      @client ||= NutanixAdapter.new(cluster)
    end
  end
end