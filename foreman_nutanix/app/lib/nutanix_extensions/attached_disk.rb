module NutanixExtensions
  module AttachedDisk
    def persisted?
    end

    def id
    end

    def _delete
    end

    def insert_attrs
      attrs = { name: device_name, size_gb: disk_size_gb }
      attrs[:source_image] = source if source.present?
      attrs
    end

    def size_gb
      disk_size_gb
    end
  end
end
