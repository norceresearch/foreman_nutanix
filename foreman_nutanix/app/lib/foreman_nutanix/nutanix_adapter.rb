module ForemanNutanix
  class NutanixAdapter
    include Enumerable

    def initialize(cluster)
      Rails.logger.info "=== NUTANIX: NutanixAdapter::initialize cluster=#{cluster} ==="
      @cluster = cluster
    end

    # Required by Foreman - returns a collection of servers
    def servers(attrs = {})
      Rails.logger.info "=== NUTANIX: NutanixAdapter::servers called with attrs: #{attrs} ==="
      ServersCollection.new(@cluster)
    end

    # Mock servers collection for Foreman
    class ServersCollection
      def initialize(cluster)
        @cluster = cluster
      end

      def new(attrs = {})
        Rails.logger.info "=== NUTANIX: ServersCollection::new called with attrs: #{attrs} ==="
        # Return the NutanixCompute model that Foreman expects
        NutanixCompute.new(@cluster, attrs)
      end

      def each(&block)
        all.each(&block)
      end

      def get(uuid)
        Rails.logger.info "=== NUTANIX: ServersCollection::get called with uuid: #{uuid} ==="

        # Extract the actual UUID if it has a prefix
        actual_uuid = ShimClient.normalize_uuid(uuid)

        # Fetch full VM details from shim server
        response = shim.get("/api/v1/vmm/vms/#{actual_uuid}")

        if response.success?
          data = response.json

          total_cpus = (data['num_sockets'] || 1) * (data['num_cores_per_socket'] || 1)
          memory_gb = data['memory_size_bytes'] ? (data['memory_size_bytes'].to_f / 1024**3).round : 4

          vm = NutanixCompute.new(@cluster, {
            identity: data['ext_id'],
            name: data['name'],
            description: data['description'],
            cpus: total_cpus,
            memory: memory_gb,
            power_state: data['power_state'],
            mac_address: data['mac_address'],
            ip_addresses: data['ip_addresses'] || [],
            create_time: data['create_time'],
            boot_method: data['boot_method'],
            secure_boot: data['secure_boot'],
            gpus: data['gpus'],
            disk_size_gb: data['disk_size_bytes'].to_i / (1024**3),
            network_id: data['network_id'],
            storage_container: data['container_id'],
          })
          vm.instance_variable_set(:@persisted, true)
          vm
        elsif response.code == '404'
          Rails.logger.warn "=== NUTANIX: VM not found (deleted from Nutanix?): #{uuid} ==="
          # Return nil so Foreman knows the VM doesn't exist
          nil
        else
          Rails.logger.error "=== NUTANIX: ServersCollection::get failed: #{response.code} - #{response.body} ==="
          nil
        end
      rescue StandardError => e
        Rails.logger.error "=== NUTANIX: ServersCollection::get error: #{e.message} ==="
        nil
      end

      def all(opts = {})
        Rails.logger.info "=== NUTANIX: ServersCollection::all called with opts: #{opts} ==="

        # Fetch VMs from shim server (now includes MAC and IP)
        data = shim.get('/api/v1/vmm/list-vms').json

        # Filter VMs by cluster
        filtered_data = data.select { |vm| vm['cluster_ext_id'] == @cluster }

        # Convert to NutanixCompute instances
        filtered_data.map do |vm_data|
          total_cpus = (vm_data['num_sockets'] || 1) * (vm_data['num_cores_per_socket'] || 1)
          memory_gb = vm_data['memory_size_bytes'] ? (vm_data['memory_size_bytes'].to_f / 1024**3).round : 4

          vm = NutanixCompute.new(@cluster, {
            identity: vm_data['ext_id'],
            name: vm_data['name'],
            description: vm_data['description'],
            cpus: total_cpus,
            memory: memory_gb,
            power_state: vm_data['power_state'],
            mac_address: vm_data['mac_address'],
            ip_addresses: vm_data['ip_addresses'] || [],
            create_time: vm_data['create_time'],
            disk_size_gb: vm_data['disk_size_bytes'].to_i / (1024**3),
          })
          vm.instance_variable_set(:@persisted, true)
          vm
        end
      rescue StandardError => e
        Rails.logger.error "=== NUTANIX: Error fetching VMs: #{e.message} ==="
        []
      end

      private

      # ServersCollection holds no reference to the ComputeResource, so it builds
      # its own client off the shim server address in the environment.
      def shim
        @shim ||= ShimClient.new
      end
    end
  end
end
