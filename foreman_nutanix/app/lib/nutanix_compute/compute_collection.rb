module NutanixCompute
  class ComputeCollection
    include Enumerable

    def initialize(client, zone, attrs = {})
      instances = client.instances(zone, **attrs)
      @virtual_machines = instances.map do |vm|
        ForemanNutanix::NutanixCompute.new client: client,
          zone: zone,
          identity: vm.id,
          instance: vm
      end
    end

    def each(&block)
      @virtual_machines.each(&block)
    end

    def all(_opts = {})
      @virtual_machines
    end
  end
end
