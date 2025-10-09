module ForemanNutanix
  class NutanixCompute
    attr_reader :identity, :name, :hostname, :creation_timestamp, :machine_type, :network_interfaces, :volumes,
      :associate_external_ip, :network, :zone, :zone_name, :image_id, :disks, :metadata

    def initialize(client:, zone:, identity: nil, instance: nil, args: {})
      @zone = zone
      @identity = identity
      @instance = instance

      load if identity && instance.nil?
      load_attributes(args)
    end

    def persisted?
      true
    end

    def ready?
      status == 'RUNNING'
    end

    def reload
      return unless identity
      load
      self
    end

    # @returns [String] one of PROVISIONING, STAGING, RUNNING, STOPPING, SUSPENDING, SUSPENDED, REPAIRING, and TERMINATED
    # if nil, instance is not persisted as VM on GCE
    def status
      persisted? && @instance.status
    end
    alias_method :state, :status

    def start
      raise Foreman::Exception('unable to start machine that is not persisted') unless persisted?
      @client.start(@zone, identity)
    end

    def stop
      raise Foreman::Exception('unable to stop machine that is not persisted') unless persisted?
      @client.stop(@zone, identity)
    end

    def to_s
      @name
    end

    def interfaces
      @network_interfaces
    end

    def create_volumes
      @volumes.each do |vol|
        @client.insert_disk(@zone, vol.insert_attrs)
        wait_for { @client.disk(@zone, vol.device_name).status == 'READY' }
      end
    end

    def destroy_volumes
      @volumes.each do |volume|
        @client.delete_disk(@zone, volume.device_name)
      end
    end

    def create_instance
      args = NutanixCloudCompute::ComputeAttributes.new(@client).for_create(self)
      @client.insert_instance(@zone, args)
    end

    def set_disk_auto_delete
      @client.set_disk_auto_delete(@zone, @name)
    end

    def pretty_machine_type
      return @machine_type unless @instance
      @instance.machine_type.split('/').last
    end

    def vm_description
      pretty_machine_type
    end

    def vm_ip_address
      return if @instance.network_interfaces.empty?

      @instance.network_interfaces.first.access_configs.first&.nat_i_p
    end
    alias_method :public_ip_address, :vm_ip_address

    def private_ip_address
      return unless @instance.network_interfaces.any?

      @instance.network_interfaces.first.network_i_p
    end

    def pretty_image_name
      return unless @instance.disks.any?

      disk_name = @instance.disks.first.source.split('/').last
      image_name = @client.disk(@zone_name, disk_name).source_image

      image_name.split('/').last
    end

    def volumes_attributes=(_attrs)
    end

    def serial_port_output
      @client.serial_port_output(@zone, @identity)&.contents
    end

    def ip_addresses
      [vm_ip_address, private_ip_address]
    end

    def wait_for(&block)
      @client.wait_for(&block)
    end

    private

    def load
      @instance = @client.instance(@zone.split('/').last, identity)
    end

    def load_attributes(args_for_new)
      klass = NutanixCloudCompute::ComputeAttributes.new(@client)
      attrs = @instance ? klass.for_instance(@instance) : klass.for_new(args_for_new)
      attrs.each { |name, value| instance_variable_set("@#{name}", value) }
    end
  end
end
