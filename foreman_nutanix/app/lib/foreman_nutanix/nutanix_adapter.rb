module ForemanNutanix
  class NutanixAdapter
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

      def get(uuid)
        Rails.logger.info "=== NUTANIX: ServersCollection::get called with uuid: #{uuid} ==="
        # Return the NutanixCompute model
        NutanixCompute.new(@cluster, { identity: uuid, name: uuid })
      end

      def all(opts = {})
        Rails.logger.info "=== NUTANIX: ServersCollection::all called with opts: #{opts} ==="

        # Fetch VMs from shim server
        base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
        uri = URI("#{base.chomp('/')}/api/v1/vmm/list-vms")
        response = Net::HTTP.get_response(uri)
        data = JSON.parse(response.body)

        # Filter VMs by cluster
        filtered_data = data.select { |vm| vm['cluster_ext_id'] == @cluster }

        # Convert to NutanixCompute instances
        filtered_data.map do |vm_data|
          # Calculate total CPUs from sockets and cores
          total_cpus = (vm_data['num_sockets'] || 1) * (vm_data['num_cores_per_socket'] || 1)
          # Convert memory from bytes to GB
          memory_gb = vm_data['memory_size_bytes'] ? (vm_data['memory_size_bytes'].to_f / 1024**3).round : 4

          vm = NutanixCompute.new(@cluster, {
            identity: vm_data['ext_id'],
            name: vm_data['name'],
            cpus: total_cpus,
            memory: memory_gb,
            power_state: vm_data['power_state']
          })
          # Mark as persisted since these are existing VMs
          vm.instance_variable_set(:@persisted, true)
          vm
        end
      rescue StandardError => e
        Rails.logger.error "=== NUTANIX: Error fetching VMs: #{e.message} ==="
        []
      end
    end
  end
end