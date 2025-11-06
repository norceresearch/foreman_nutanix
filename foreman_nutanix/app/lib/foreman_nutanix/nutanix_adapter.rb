module ForemanNutanix
  class NutanixAdapter
    def initialize(cluster)
      Rails.logger.info "=== NUTANIX: NutanixAdapter::initialize cluster=#{cluster} ==="
      @cluster = cluster
    end

    # Required by Foreman - returns a collection of servers
    def servers
      Rails.logger.info "=== NUTANIX: NutanixAdapter::servers called ==="
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

      def all
        Rails.logger.info "=== NUTANIX: ServersCollection::all called ==="
        # Return empty array for now
        []
      end
    end
  end
end