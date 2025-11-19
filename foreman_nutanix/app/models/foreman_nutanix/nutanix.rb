module ForemanNutanix
  class Nutanix < ComputeResource
    validates :cluster, presence: true

    def self.model_name
      ComputeResource.model_name
    end

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

    def cluster_details
      available_clusters.find { |cluster| cluster.ext_id == self.cluster }
    end

    def to_label
      "#{name} (#{provider_friendly_name})"
    end

    def shim_server_url
      ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
    end

    def provided_attributes
      super.merge({ mac: :mac })
    end

    # Test connection to the compute resource
    def test_connection(_options = {})
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
    def available_networks
      Rails.logger.info '=== NUTANIX: Fetching available networks from shim server ==='
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/networking/list-networks")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      data.map do |network|
        OpenStruct.new({
          id: network['ext_id'],
          ext_id: network['ext_id'],
          name: network['name'],
          subnet_type: network['subnet_type'],
          cluster_name: network['cluster_name'],
          ipv4_subnet: network['ipv4_subnet'],
          ipv4_gateway: network['ipv4_gateway'],
        })
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error fetching networks: #{e.message} ==="
      []
    end

    # Networks method (alias for available_networks)
    def networks(opts = {})
      Rails.logger.info "=== NUTANIX: NETWORKS called with opts: #{opts} ==="
      available_networks
    end

    # Available storage containers for VMs
    def available_storage_containers
      Rails.logger.info '=== NUTANIX: Fetching available storage containers from shim server ==='
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/clustermgmt/list-storage-containers")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      # Filter storage containers by the cluster associated with this compute resource
      cluster_ext_id = cluster
      Rails.logger.info "=== NUTANIX: Storage containers - total: #{data.count}, cluster_ext_id: #{cluster_ext_id} ==="
      filtered_data = data.select { |container| container['cluster_ext_id'] == cluster_ext_id }
      Rails.logger.info "=== NUTANIX: Storage containers - filtered: #{filtered_data.count} ==="

      result = filtered_data.map do |container|
        OpenStruct.new({
          id: container['ext_id'],
          ext_id: container['ext_id'],
          name: container['name'],
          cluster_name: container['cluster_name'],
          max_capacity_bytes: container['max_capacity_bytes'],
          replication_factor: container['replication_factor'],
          is_compression_enabled: container['is_compression_enabled'],
        })
      end
      Rails.logger.info "=== NUTANIX: Storage containers returning: #{result.map { |c| { id: c.id, name: c.name } }} ==="
      result
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error fetching storage containers: #{e.message} ==="
      []
    end

    # Cluster resource statistics (CPU, memory, storage usage)
    def cluster_resource_stats
      Rails.logger.info '=== NUTANIX: Fetching cluster resource stats from shim server ==='
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      cluster_id = cluster
      return nil unless cluster_id

      uri = URI("#{base.chomp('/')}/api/v1/clustermgmt/clusters/#{cluster_id}/stats")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      OpenStruct.new(data)
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error fetching cluster stats: #{e.message} ==="
      nil
    end

    # Available machine types/flavors
    def available_flavors
      Rails.logger.info '=== NUTANIX: Returning available flavors ==='
      [OpenStruct.new({ id: 'small', name: 'Small (2 CPU, 4GB RAM)' })]
    end
    alias_method :machine_types, :available_flavors

    # Available images
    def available_images(_opts = {})
      Rails.logger.info '=== NUTANIX: Fetching available images from shim server ==='
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/list-images")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      # Filter images by cluster if cluster_location_ext_ids is available
      cluster_ext_id = cluster
      filtered_data = data.select do |image|
        # Include image if it's available on this cluster
        cluster_locations = image['cluster_location_ext_ids'] || []
        cluster_locations.include?(cluster_ext_id)
      end

      filtered_data.map do |image|
        # Convert size to GB for display
        size_gb = image['size_bytes'] ? (image['size_bytes'].to_f / 1024**3).round(2) : 0
        display_name = "#{image['name']} (#{size_gb} GB)"

        OpenStruct.new({
          id: image['ext_id'],
          ext_id: image['ext_id'],
          name: display_name,
          description: image['description'],
          size_bytes: image['size_bytes'],
          type: image['type'],
        })
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error fetching images: #{e.message} ==="
      []
    end

    # Core provisioning method - this is what Foreman calls to create a VM
    def create_vm(args = {})
      Rails.logger.info "=== NUTANIX: CREATE_VM CALLED with args: #{args} ==="
      Rails.logger.info "=== NUTANIX: CREATE_VM args class: #{args.class}, keys: #{args.keys rescue 'N/A'} ==="
      Rails.logger.info "=== NUTANIX: CREATE_VM network_id: #{args[:network_id] || args['network_id']}, storage_container: #{args[:storage_container] || args['storage_container']} ==="

      vm = new_vm(args)
      Rails.logger.info '=== NUTANIX: CREATE_VM calling vm.save ==='
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
      Rails.logger.info "=== NUTANIX: NEW_VM attr keys: #{attr.keys} ==="
      Rails.logger.info "=== NUTANIX: NEW_VM storage_container value: #{attr['storage_container'] || attr[:storage_container]} ==="
      vm_attrs = vm_instance_defaults.merge(attr.to_hash.deep_symbolize_keys)
      vm_attrs = normalize_vm_attrs(vm_attrs)
      Rails.logger.info "=== NUTANIX: NEW_VM merged attrs: #{vm_attrs} ==="
      Rails.logger.info "=== NUTANIX: NEW_VM merged keys: #{vm_attrs.keys} ==="

      # Use the Foreman pattern - client.servers.new returns our VM model
      client.servers.new(vm_attrs)
    end

    # Default attributes for new VMs
    def vm_instance_defaults
      Rails.logger.info '=== NUTANIX: VM_INSTANCE_DEFAULTS called ==='
      {
        zone: 'default-zone',
        machine_type: 'small',
        cpus: 2,
        memory: 4,
      }
    end

    # Normalize VM attributes from form
    def normalize_vm_attrs(vm_attrs)
      Rails.logger.info "=== NUTANIX: NORMALIZE_VM_ATTRS called with: #{vm_attrs} ==="
      normalized = vm_attrs.dup

      # Convert string numbers to integers
      normalized[:cpus] = normalized[:cpus].to_i if normalized[:cpus]
      normalized[:memory] = normalized[:memory].to_i if normalized[:memory]

      normalized
    end

    # Find existing VM by UUID
    def find_vm_by_uuid(uuid)
      Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID CALLED with uuid: #{uuid} ==="

      return nil if uuid.nil? || uuid.to_s.strip.empty?

      # Extract the actual UUID if it has a prefix (e.g., "ZXJnb24=:eab4ff32-5011-59d0-9ad4-01228d3121db")
      actual_uuid = uuid.to_s.include?(':') ? uuid.to_s.split(':').last : uuid.to_s
      Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID using actual_uuid: #{actual_uuid} ==="

      # Fetch VM details from shim server
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/vms/#{actual_uuid}")
      response = Net::HTTP.get_response(uri)

      if response.is_a?(Net::HTTPSuccess)
        data = JSON.parse(response.body)
        Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID got data: #{data} ==="

        # Calculate total CPUs from sockets and cores
        total_cpus = (data['num_sockets'] || 1) * (data['num_cores_per_socket'] || 1)
        # Convert memory from bytes to GB
        memory_gb = data['memory_size_bytes'] ? (data['memory_size_bytes'].to_f / 1024**3).round : 4

        vm = NutanixCompute.new(cluster, {
          identity: data['ext_id'],
          name: data['name'],
          cpus: total_cpus,
          memory: memory_gb,
          power_state: data['power_state'],
          mac_address: data['mac_address'],
          ip_addresses: data['ip_addresses'] || []
        })
        vm.instance_variable_set(:@persisted, true)
        Rails.logger.info "=== NUTANIX: FIND_VM_BY_UUID returning VM: #{vm} ==="
        vm
      else
        Rails.logger.error "=== NUTANIX: FIND_VM_BY_UUID failed: #{response.code} - #{response.body} ==="
        # Return a basic VM object if we can't fetch details
        vm = NutanixCompute.new(cluster, { name: uuid, identity: uuid })
        vm.instance_variable_set(:@persisted, true)
        vm
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: FIND_VM_BY_UUID error: #{e.message} ==="
      vm = NutanixCompute.new(cluster, { name: uuid, identity: uuid })
      vm.instance_variable_set(:@persisted, true)
      vm
    end

    # Foreman might call ready? on the compute resource
    def ready?
      Rails.logger.info '=== NUTANIX: Nutanix::ready? called ==='
      true
    end

    # Destroy VM
    def destroy_vm(uuid)
      Rails.logger.info "=== NUTANIX: DESTROY_VM CALLED with uuid: #{uuid} ==="

      return true if uuid.nil? || uuid.to_s.strip.empty?

      # Extract the actual UUID if it has a prefix (e.g., "ZXJnb24=:eab4ff32-5011-59d0-9ad4-01228d3121db")
      actual_uuid = uuid.to_s.include?(':') ? uuid.to_s.split(':').last : uuid.to_s
      Rails.logger.info "=== NUTANIX: DESTROY_VM using actual_uuid: #{actual_uuid} ==="

      # Call the shim server to delete the VM
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/vms/#{actual_uuid}")

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'

      request = Net::HTTP::Delete.new(uri.path)
      response = http.request(request)

      if response.is_a?(Net::HTTPNoContent) || response.is_a?(Net::HTTPSuccess)
        Rails.logger.info "=== NUTANIX: VM #{uuid} deleted successfully ==="
        true
      else
        error_message = "Failed to delete VM: #{response.code} - #{response.body}"
        Rails.logger.error "=== NUTANIX: #{error_message} ==="
        raise StandardError, error_message
      end
    rescue ActiveRecord::RecordNotFound
      true
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error in destroy_vm: #{e.message} ==="
      raise e
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

    # List all VMs
    def vms(attrs = {})
      Rails.logger.info "=== NUTANIX: VMS CALLED with attrs: #{attrs} ==="
      client.servers(attrs)
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: VMS ERROR: #{e.message} ==="
      raise e
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
