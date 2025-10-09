module NutanixCompute
  class ComputeAttributes
    def initialize(client)
      @client = client
    end

    def for_new(args)
      name = parameterize_name(args[:name])
      network = args[:network] || 'default'
      associate_external_ip = ActiveModel::Type::Boolean.new.cast(args[:associate_external_ip])

      { name: name, hostname: name,
        machine_type: args[:machine_type],
        network: network, associate_external_ip: associate_external_ip,
        network_interfaces: construct_network(network, associate_external_ip, args[:network_interfaces] || []),
        image_id: args[:image_id],
        volumes: construct_volumes(name, args[:image_id], args[:volumes]),
        metadata: construct_metadata(args) }
    end

    def for_create(instance)
      {
        name: instance.name,
        machine_type: "zones/#{instance.zone}/machineTypes/#{instance.machine_type}",
        disks: instance.volumes.map.with_index { |vol, i| { source: "zones/#{instance.zone}/disks/#{vol.device_name}", boot: i.zero? } },
        network_interfaces: instance.network_interfaces,
        metadata: instance.metadata,
      }
    end

    def for_instance(instance)
      {
        name: instance.name, hostname: instance.name,
        creation_timestamp: instance.creation_timestamp.to_datetime,
        zone_name: instance.zone.split('/').last,
        machine_type: instance.machine_type,
        network: instance.network_interfaces[0].network.split('/').last,
        network_interfaces: instance.network_interfaces,
        volumes: instance.disks, metadata: instance.metadata
      }
    end

    private

    def parameterize_name(name)
      name&.parameterize || "foreman-#{Time.now.to_i}"
    end

    def construct_network(network_name, associate_external_ip, network_interfaces)
      # handle network_interface for external ip
      # assign  ephemeral external IP address using associate_external_ip
      raise "NOT IMPLEMENTED"
    end

    def load_image(image_id)
      return unless image_id

      @client.image(image_id.to_i)
    end

    def construct_volumes(vm_name, image_id, volumes = [])
      return [Nutanix::Cloud::Compute::V1::AttachedDisk.new(disk_size_gb: 20)] if volumes.empty?

      image = load_image(image_id)

      attached_disks = volumes.map.with_index do |vol_attrs, i|
        name = "#{vm_name}-disk#{i + 1}"
        size = (vol_attrs[:size_gb] || vol_attrs[:disk_size_gb]).to_i

        Nutanix::Cloud::Compute::V1::AttachedDisk.new(device_name: name, disk_size_gb: size)
      end

      attached_disks.first.source = image&.self_link if image&.self_link
      attached_disks
    end

    # Note - GCE only supports cloud-init for Container Optimized images and
    # for custom images with cloud-init setup
    def construct_metadata(args)
      ssh_keys = { key: 'ssh-keys', value: "#{args[:username]}:#{args[:public_key]}" }

      return { items: [ssh_keys] } if args[:user_data].blank?

      { items: [ssh_keys, { key: 'user-data', value: args[:user_data] }] }
    end
  end
end
