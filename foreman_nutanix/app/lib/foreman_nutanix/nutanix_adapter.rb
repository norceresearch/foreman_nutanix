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
        # Return a sample VM for testing
        # In production, this would fetch actual VMs from Nutanix API
        vm = NutanixCompute.new(@cluster, { 
          identity: 'test-vm-1', 
          name: 'test-vm-1',
          machine_type: 'small'
        })
        # Mark as persisted so it shows as 'running'
        vm.instance_variable_set(:@persisted, true)
        [vm]
      end
    end
  end
end