module ForemanNutanix
  class NutanixCompute
    attr_reader :identity, :name, :hostname, :cluster, :args
    attr_accessor :zone, :machine_type, :network, :image_id, :associate_external_ip, :cpus, :memory, :power_state

    def initialize(cluster = nil, args = {})
      Rails.logger.info "=== NUTANIX: NutanixCompute::initialize cluster=#{cluster} args=#{args} ==="
      @cluster = cluster
      @args = args
      @name = args[:name] || "nutanix-vm-#{Time.now.to_i}"
      @identity = args[:identity] || args[:uuid] || @name
      @hostname = args[:hostname] || @name
      @zone = args[:zone] || 'default-zone'
      @machine_type = args[:machine_type] || args[:flavor_id] || 'small'
      @network = args[:network] || args[:network_id] || 'default-network'
      @image_id = args[:image_id]
      @associate_external_ip = args[:associate_external_ip] || true
      @cpus = args[:cpus] || 2
      @memory = args[:memory] || 4
      @power_state = args[:power_state]
      @persisted = false
    end

    # Required by Foreman - indicates if VM exists
    def persisted?
      Rails.logger.info "=== NUTANIX: NutanixCompute::persisted? called ==="
      @persisted
    end

    # Required by Foreman - save the VM (actually create it)
    def save
      Rails.logger.info "=== NUTANIX: NutanixCompute::save called ==="
      # Mock the save operation
      @persisted = true
      @identity ||= "vm-#{Time.now.to_i}"
      true
    end

    # Required by Foreman - VM status
    def ready?
      Rails.logger.info "=== NUTANIX: NutanixCompute::ready? called ==="
      persisted? # Only ready if saved
    end

    # Required by Foreman - VM status
    def state
      Rails.logger.info "=== NUTANIX: NutanixCompute::state called ==="
      return 'pending' unless persisted?

      # Map Nutanix power states to Foreman-friendly states
      case @power_state
      when 'ON'
        'running'
      when 'OFF'
        'stopped'
      when 'PAUSED'
        'paused'
      else
        'unknown'
      end
    end
    alias_method :status, :state

    # Required by Foreman - reload VM state
    def reload
      Rails.logger.info "=== NUTANIX: NutanixCompute::reload called ==="
      self
    end

    # Required by Foreman - start VM
    def start(args = {})
      Rails.logger.info "=== NUTANIX: NutanixCompute::start called with args: #{args} ==="
      true
    end

    # Required by Foreman - stop VM  
    def stop(args = {})
      Rails.logger.info "=== NUTANIX: NutanixCompute::stop called with args: #{args} ==="
      true
    end

    # Required by Foreman - CPU count
    def cpu
      Rails.logger.info "=== NUTANIX: NutanixCompute::cpu called ==="
      @cpus.to_s
    end

    # Required by Foreman - memory in GB
    def memory
      Rails.logger.info "=== NUTANIX: NutanixCompute::memory called ==="
      @memory
    end

    # Required by Foreman - string representation
    def to_s
      @name
    end

    # Required by Foreman - public IP address
    def vm_ip_address
      Rails.logger.info "=== NUTANIX: NutanixCompute::vm_ip_address called ==="
      persisted? ? '192.168.1.100' : nil
    end
    alias_method :public_ip_address, :vm_ip_address

    # Required by Foreman - private IP address
    def private_ip_address
      Rails.logger.info "=== NUTANIX: NutanixCompute::private_ip_address called ==="
      persisted? ? '10.0.0.100' : nil
    end

    # Required by Foreman - all IP addresses
    def ip_addresses
      Rails.logger.info "=== NUTANIX: NutanixCompute::ip_addresses called ==="
      persisted? ? [vm_ip_address, private_ip_address] : []
    end

    # Required by Foreman - MAC address
    def mac
      Rails.logger.info "=== NUTANIX: NutanixCompute::mac called ==="
      persisted? ? '00:50:56:aa:bb:cc' : nil
    end

    # Required by Foreman - VM description
    def vm_description
      Rails.logger.info "=== NUTANIX: NutanixCompute::vm_description called ==="
      pretty_machine_type
    end

    # Required by Foreman - pretty machine type
    def pretty_machine_type
      Rails.logger.info "=== NUTANIX: NutanixCompute::pretty_machine_type called ==="
      "#{@cpus} CPUs, #{memory}GB RAM"
    end

    # Required by Foreman - volumes/disks
    def volumes
      Rails.logger.info "=== NUTANIX: NutanixCompute::volumes called ==="
      [OpenStruct.new({ name: 'disk-1', size_gb: 20 })]
    end

    # Required by Foreman - volumes_attributes setter
    def volumes_attributes=(_attrs)
      Rails.logger.info "=== NUTANIX: NutanixCompute::volumes_attributes= called ==="
    end

    # Required by Foreman - network interfaces
    def interfaces
      Rails.logger.info "=== NUTANIX: NutanixCompute::interfaces called ==="
      [OpenStruct.new({ name: 'eth0', network: @network })]
    end

    # Required by Foreman - network interfaces access
    def network_interfaces
      Rails.logger.info "=== NUTANIX: NutanixCompute::network_interfaces called ==="
      interfaces
    end

    # Required by Foreman - console/serial output
    def serial_port_output
      Rails.logger.info "=== NUTANIX: NutanixCompute::serial_port_output called ==="
      "Mock serial console output for #{@name}"
    end

    # Required by Foreman - wait for condition
    def wait_for(&block)
      Rails.logger.info "=== NUTANIX: NutanixCompute::wait_for called ==="
      yield if block_given?
    end

    # Required by Foreman - destroy VM
    def destroy
      Rails.logger.info "=== NUTANIX: NutanixCompute::destroy called ==="
      @persisted = false
      true
    end
  end
end