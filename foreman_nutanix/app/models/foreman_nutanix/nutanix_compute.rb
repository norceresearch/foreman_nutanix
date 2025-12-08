module ForemanNutanix
  class NutanixCompute
    attr_reader :identity, :name, :hostname, :cluster, :args
    attr_accessor :zone, :machine_type,
      :network, :image_id, :associate_external_ip,
      :cpus, :memory, :power_state, :subnet_ext_id,
      :storage_container_ext_id, :num_sockets, :num_cores_per_socket,
      :disk_size_bytes, :description, :network_id, :storage_container,
      :disk_size_gb, :power_on, :mac_address, :vm_ip_addresses, :create_time,
      :boot_method, :secure_boot, :gpus

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

      # Provisioning-specific attributes
      @network_id = args[:network_id] || args[:network]
      @storage_container = args[:storage_container]
      @disk_size_gb = args[:disk_size_gb] || 50
      @power_on = args.key?(:power_on) ? args[:power_on] : true # Default to true
      @subnet_ext_id = args[:subnet_ext_id] || @network_id
      @storage_container_ext_id = args[:storage_container_ext_id] || @storage_container
      @num_sockets = args[:num_sockets] || 1
      @num_cores_per_socket = args[:num_cores_per_socket] || @cpus
      @disk_size_bytes = args[:disk_size_bytes] || (@disk_size_gb.to_i * 1024**3)
      @description = args[:description] || ''

      # VM details from Nutanix
      @mac_address = args[:mac_address]
      @vm_ip_addresses = args[:ip_addresses] || []
      @create_time = args[:create_time]

      # Boot config
      @boot_method = args[:boot_method]
      @secure_boot = args[:secure_boot]

      # GPUs
      @gpus = args[:gpus]
    end

    # Required by Foreman - indicates if VM exists
    def persisted?
      Rails.logger.info '=== NUTANIX: NutanixCompute::persisted? called ==='
      @persisted
    end

    # Required by Foreman - save the VM (actually create it)
    def save
      Rails.logger.info '=== NUTANIX: NutanixCompute::save called ==='
      Rails.logger.info "=== NUTANIX: VM attributes - network_id: #{@network_id}, storage_container: #{@storage_container}, subnet_ext_id: #{@subnet_ext_id}, storage_container_ext_id: #{@storage_container_ext_id} ==="

      # Build the provision request payload
      # Convert memory from GB to bytes (1 GB = 1024^3 bytes)
      memory_bytes = (@memory || 4).to_i * 1024**3

      # Use form values, falling back to internal values
      actual_subnet = @subnet_ext_id || @network_id
      actual_storage = @storage_container_ext_id || @storage_container
      actual_disk_bytes = @disk_size_bytes || (@disk_size_gb.to_i * 1024**3)

      # Validate required fields
      if actual_subnet.nil? || actual_subnet.to_s.strip.empty?
        raise StandardError, 'Network/Subnet is required for VM provisioning'
      end
      if actual_storage.nil? || actual_storage.to_s.strip.empty?
        raise StandardError, 'Storage Container is required for VM provisioning'
      end

      provision_request = {
        name: @name,
        cluster_ext_id: @cluster,
        subnet_ext_id: actual_subnet,
        storage_container_ext_id: actual_storage,
        num_sockets: @num_sockets.to_i,
        num_cores_per_socket: @num_cores_per_socket.to_i,
        memory_size_bytes: memory_bytes,
        disk_size_bytes: actual_disk_bytes.to_i,
        description: @description || '',
        power_on: @power_on.nil? || @power_on, # Default to true if not set
        secure_boot: @secure_boot,
        boot_method: @boot_method,
      }

      Rails.logger.info "=== NUTANIX: Provisioning VM with request: #{provision_request} ==="

      # Call the shim server to provision the VM
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/provision-vm")

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'

      request = Net::HTTP::Post.new(uri.path)
      request['Content-Type'] = 'application/json'
      request.body = provision_request.to_json

      response = http.request(request)

      if response.is_a?(Net::HTTPSuccess)
        result = JSON.parse(response.body)
        Rails.logger.info "=== NUTANIX: VM provisioned successfully: #{result} ==="

        # Update identity with the real ext_id from Nutanix
        @identity = result['ext_id']
        @persisted = true
        true
      else
        error_message = "Failed to provision VM: #{response.code} - #{response.body}"
        Rails.logger.error "=== NUTANIX: #{error_message} ==="
        raise StandardError, error_message
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error in save: #{e.message} ==="
      raise e
    end

    # Required by Foreman - VM status
    # Returns true if VM is powered on and ready to use
    def ready?
      is_ready = persisted? && @power_state == 'ON'
      Rails.logger.info "=== NUTANIX: NutanixCompute::ready? called, persisted=#{persisted?}, power_state=#{@power_state}, returning #{is_ready} ==="
      is_ready
    end

    # Power state accessor that Foreman might call directly
    def power_state
      Rails.logger.info "=== NUTANIX: NutanixCompute::power_state called, returning #{@power_state} ==="
      @power_state
    end

    # Required by Foreman - VM status
    def state
      Rails.logger.info "=== NUTANIX: NutanixCompute::state called, power_state=#{@power_state} ==="
      return 'pending' unless persisted?

      # Map Nutanix power states to Foreman-friendly states
      result = case @power_state
               when 'ON'
                 'running'
               when 'OFF'
                 'stopped'
               when 'PAUSED'
                 'paused'
               else
                 'unknown'
               end
      Rails.logger.info "=== NUTANIX: NutanixCompute::state returning '#{result}' ==="
      result
    end
    alias_method :status, :state

    # Required by Foreman - reload VM state
    def reload
      Rails.logger.info '=== NUTANIX: NutanixCompute::reload called ==='
      self
    end

    # Required by Foreman - start VM
    def start(args = {})
      Rails.logger.info "=== NUTANIX: NutanixCompute::start called with args: #{args} ==="
      return false unless persisted?

      # Extract actual UUID (handle ZXJnb24=:uuid format)
      actual_uuid = @identity.to_s.include?(':') ? @identity.to_s.split(':').last : @identity.to_s

      # Call the shim server to power on the VM
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/vms/#{actual_uuid}/power-state")

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'

      request = Net::HTTP::Post.new(uri.path)
      request['Content-Type'] = 'application/json'
      request.body = { action: 'POWER_ON' }.to_json

      response = http.request(request)

      if response.is_a?(Net::HTTPSuccess)
        Rails.logger.info "=== NUTANIX: VM #{actual_uuid} powered on successfully ==="
        @power_state = 'ON'
        true
      else
        error_message = "Failed to power on VM: #{response.code} - #{response.body}"
        Rails.logger.error "=== NUTANIX: #{error_message} ==="
        raise StandardError, error_message
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error in start: #{e.message} ==="
      raise e
    end

    # Required by Foreman - stop VM
    def stop(args = {})
      Rails.logger.info "=== NUTANIX: NutanixCompute::stop called with args: #{args} ==="
      return false unless persisted?

      # Extract actual UUID (handle ZXJnb24=:uuid format)
      actual_uuid = @identity.to_s.include?(':') ? @identity.to_s.split(':').last : @identity.to_s

      # Call the shim server to power off the VM
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/vms/#{actual_uuid}/power-state")

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'

      request = Net::HTTP::Post.new(uri.path)
      request['Content-Type'] = 'application/json'
      request.body = { action: 'POWER_OFF' }.to_json

      response = http.request(request)

      if response.is_a?(Net::HTTPSuccess)
        Rails.logger.info "=== NUTANIX: VM #{actual_uuid} powered off successfully ==="
        @power_state = 'OFF'
        true
      else
        error_message = "Failed to power off VM: #{response.code} - #{response.body}"
        Rails.logger.error "=== NUTANIX: #{error_message} ==="
        raise StandardError, error_message
      end
    rescue StandardError => e
      Rails.logger.error "=== NUTANIX: Error in stop: #{e.message} ==="
      raise e
    end

    # Required by Foreman - CPU count
    def cpu
      Rails.logger.info '=== NUTANIX: NutanixCompute::cpu called ==='
      @cpus.to_s
    end

    # Required by Foreman - memory in GB
    def memory
      Rails.logger.info '=== NUTANIX: NutanixCompute::memory called ==='
      @memory
    end

    # Required by Foreman - string representation
    def to_s
      @name
    end

    # Required by Foreman - creation timestamp
    def creation_timestamp
      Rails.logger.info '=== NUTANIX: NutanixCompute::creation_timestamp called ==='
      return nil unless @create_time

      begin
        if @create_time.is_a?(String)
          Time.parse(@create_time)
        else
          @create_time
        end
      rescue StandardError => e
        Rails.logger.error "=== NUTANIX: Error parsing create_time: #{e.message} ==="
        nil
      end
    end

    # Required by Foreman - image name for display
    def pretty_image_name
      Rails.logger.info '=== NUTANIX: NutanixCompute::pretty_image_name called ==='
      # We don't track the source image yet
      nil
    end

    # Required by Foreman - public IP address
    def vm_ip_address
      Rails.logger.info '=== NUTANIX: NutanixCompute::vm_ip_address called ==='
      return nil unless persisted?
      @vm_ip_addresses&.first
    end
    alias_method :public_ip_address, :vm_ip_address

    # Required by Foreman - private IP address
    def private_ip_address
      Rails.logger.info '=== NUTANIX: NutanixCompute::private_ip_address called ==='
      return nil unless persisted?
      # Return second IP if available, otherwise same as public
      (@vm_ip_addresses&.length.to_i > 1) ? @vm_ip_addresses[1] : @vm_ip_addresses&.first
    end

    # Required by Foreman - all IP addresses
    def ip_addresses
      Rails.logger.info '=== NUTANIX: NutanixCompute::ip_addresses called ==='
      persisted? ? (@vm_ip_addresses || []) : []
    end

    # Required by Foreman - MAC address
    def mac
      Rails.logger.info "=== NUTANIX: NutanixCompute::mac called, persisted=#{persisted?}, mac_address=#{@mac_address} ==="
      persisted? ? @mac_address : nil
    end

    # Required by Foreman - MAC addresses hash for VM association
    def mac_addresses
      Rails.logger.info "=== NUTANIX: NutanixCompute::mac_addresses called, mac_address=#{@mac_address} ==="
      return {} unless @mac_address
      { 'nic0' => @mac_address }
    end

    # Required by Foreman - VM description
    def vm_description
      Rails.logger.info '=== NUTANIX: NutanixCompute::vm_description called ==='
      pretty_machine_type
    end

    # Required by Foreman - pretty machine type
    def pretty_machine_type
      Rails.logger.info '=== NUTANIX: NutanixCompute::pretty_machine_type called ==='
      "#{@cpus} CPUs, #{memory}GB RAM"
    end

    # Required by Foreman - volumes/disks
    def volumes
      Rails.logger.info '=== NUTANIX: NutanixCompute::volumes called ==='
      # [OpenStruct.new({ name: 'disk-1', size_gb: 20 })]
      []
    end

    # Required by Foreman - volumes_attributes setter
    def volumes_attributes=(_attrs)
      Rails.logger.info '=== NUTANIX: NutanixCompute::volumes_attributes= called ==='
    end

    # Required by Foreman - network interfaces
    def interfaces
      Rails.logger.info '=== NUTANIX: NutanixCompute::interfaces called ==='
      [OpenStruct.new({
        name: 'eth0',
        network: @network,
        mac: @mac_address,
        ip: @vm_ip_addresses&.first,
      })]
    end

    # Required by Foreman - network interfaces access
    def network_interfaces
      Rails.logger.info '=== NUTANIX: NutanixCompute::network_interfaces called ==='
      interfaces
    end

    # Required by Foreman - select matching NIC from compute resource
    # This is called by Foreman's match_macs_to_nics to assign MAC addresses
    def select_nic(fog_nics, nic)
      Rails.logger.info "=== NUTANIX: NutanixCompute::select_nic called with fog_nics=#{fog_nics.inspect}, nic=#{nic.inspect} ==="
      # Return the first available NIC (we only have one for now)
      fog_nics.shift
    end

    # Required by Foreman - console/serial output
    def serial_port_output
      Rails.logger.info '=== NUTANIX: NutanixCompute::serial_port_output called ==='
      "Mock serial console output for #{@name}"
    end

    # Required by Foreman - wait for condition
    def wait_for
      Rails.logger.info '=== NUTANIX: NutanixCompute::wait_for called ==='
      yield if block_given?
    end

    # Required by Foreman - destroy VM
    def destroy
      Rails.logger.info '=== NUTANIX: NutanixCompute::destroy called ==='
      @persisted = false
      true
    end
  end
end
