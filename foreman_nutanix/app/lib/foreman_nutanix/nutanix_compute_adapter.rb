module ForemanNutanix
  class NutanixComputeAdapter
    def initialize(cluster_id)
      @cluster_id = cluster_id
    end

    def project_id
      'project-id-here'
    end

    # ------ RESOURCES ------

    def insert_instance(zone, attrs = {})
      response = resource_client('instances').insert(project: project_id, zone: zone, instance_resource: attrs)
      operation_attrs = { zone: zone, operation: response.operation.id.to_s }

      wait_for do
        get('zone_operations', **operation_attrs).status == :DONE
      end

      e = get('zone_operations', **operation_attrs).error

      return response unless e

      raise ::Nutanix::Cloud::Error, e.errors.first.message
    end

    # Returns an Nutanix::Instance identified by instance_identity within given zone.
    # @param zone [String] eighter full url or just zone name
    # @param instance_identity [String] eighter an instance name or its id
    def instance(zone, instance_identity)
      get('instances', instance: instance_identity, zone: zone)
    end

    def instances(zone, **attrs)
      list('instances', zone: zone, **attrs)
    end

    def zones
      list('zones')
    end

    def networks
      list('networks')
    end

    def machine_types(zone)
      list('machine_types', zone: zone)
    end

    def start(zone, instance_identity)
      manage_instance(:start, zone: zone, instance: instance_identity)
    end

    def stop(zone, instance_identity)
      manage_instance(:stop, zone: zone, instance: instance_identity)
    end

    def delete_instance(zone, instance_identity)
      manage_instance(:delete, zone: zone, instance: instance_identity)
    end

    def image_id=(id)
      self._image_id = id
    end

    def image_id
      _image_id
    end

    def list_images
      base = ENV['NUTANIX_SHIM_SERVER_ADDR'] || 'http://localhost:8000'
      uri = URI("#{base.chomp('/')}/api/v1/vmm/list-images")
      response = Net::HTTP.get_response(uri)
      JSON.parse(response.body)
    end

    def images(filter: nil)
      list_images.filter_map do |image|
        # Filter out only images assignable to this cluster
        next unless image['cluster_location_ext_ids'].include?(@cluster_id)
        image[:id] = image['ext_id']
        image[:name] = "#{image['name']} - (#{image['type']})"
        OpenStruct.new(image)
      end
    end

    def image(uuid)
      images.find { |img| img.id == uuid }
    end

    def insert_disk(zone, disk_attrs = {})
      insert('disks', zone, disk_resource: disk_attrs)
    end

    def disk(zone, name)
      get('disks', disk: name, zone: zone)
    end

    def delete_disk(zone, disk_name)
      delete('disks', zone, disk: disk_name)
    end

    def set_disk_auto_delete(zone, instance_identity)
      instance = instance(zone, instance_identity)
      instance.disks.each do |disk|
        manage_instance :set_disk_auto_delete, zone: zone,
          device_name: disk.device_name,
          instance: instance_identity,
          auto_delete: true
      end
    end

    def serial_port_output(zone, instance_identity)
      manage_instance(:get_serial_port_output, zone: zone, instance: instance_identity)
    end

    def wait_for
      timeout = 60
      duration = 0
      start = Time.zone.now

      loop do
        break if yield

        raise "The specified wait_for timeout (#{timeout} seconds) was exceeded" if duration > timeout

        sleep(1)
        duration = Time.zone.now - start
      end

      { duration: duration }
    end

    private

    def list(resource_name, **opts)
      response = resource_client(resource_name).list(project: project_id, **opts).response
      response.items
    rescue ::Nutanix::Cloud::Error => e
      raise Foreman::WrappedException.new(e, 'Cannot list Nutanix resource %s', resource_name)
    end

    def get(resource_name, **opts)
      resource_client(resource_name).get(project: project_id, **opts)
    rescue Nutanix::Cloud::NotFoundError => e
      Foreman::Logging.exception("Could not fetch Nutanix instance [#{opts[:instance]}]", e)
      raise ActiveRecord::RecordNotFound
    rescue ::Nutanix::Cloud::Error => e
      raise Foreman::WrappedException.new(e, 'Could not fetch Nutanix resource %s', resource_name)
    end

    def insert(resource_name, zone, **opts)
      resource_client(resource_name).insert(project: project_id, zone: zone, **opts)
    rescue ::Nutanix::Cloud::Error => e
      raise Foreman::WrappedException.new(e, 'Could not create Nutanix resource %s', resource_name)
    end

    def delete(resource_name, zone, **opts)
      resource_client(resource_name).delete(project: project_id, zone: zone, **opts)
    rescue ::Nutanix::Cloud::Error => e
      raise Foreman::WrappedException.new(e, 'Could not delete Nutanix resource %s', resource_name)
    end

    def manage_instance(action, **opts)
      resource_client('instances').send(action, project: project_id, **opts)
    rescue ::Nutanix::Cloud::Error => e
      raise Foreman::WrappedException.new(e, 'Could not %s Nutanix resource %s', action.to_s, resource_name)
    end

    def resource_client(resource_name)
      ::Nutanix::Cloud::Compute.public_send(resource_name) do |config|
        config.credentials = @auth_json
      end
    end

    def all_projects
      %w[centos-cloud cos-cloud coreos-cloud debian-cloud opensuse-cloud
         rhel-cloud rhel-sap-cloud suse-cloud suse-sap-cloud
         ubuntu-os-cloud windows-cloud windows-sql-cloud].freeze
    end
  end
end
