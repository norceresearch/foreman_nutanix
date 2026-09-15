module ForemanNutanix
  # The compute profile form is a single select, so a GPU choice is stored as one
  # composite string: "<device_id>:<vendor_name>:<gpu_type>". This module owns that
  # format at both ends - Nutanix#available_gpus builds it, NutanixCompute#save
  # parses it - so the two can never disagree about it.
  #
  # Plain Ruby, no Rails: loaded directly by the standalone tests. See test/README.md.
  module GpuProfile
    SEPARATOR = ':'.freeze
    PARTS = %w[device_id vendor_name gpu_type].freeze

    module_function

    def blank?(value)
      value.nil? || value.to_s.strip.empty?
    end

    # Only offer a profile that can survive the round trip: passthrough (the shim
    # rejects VIRTUAL), and every composite part present. A profile missing one
    # part builds a composite that #parse rejects, which would provision a VM with
    # no GPU while reporting success.
    def usable?(profile)
      return false unless profile[PARTS.last].to_s.start_with?('PASSTHROUGH')

      PARTS.none? { |part| blank?(profile[part]) }
    end

    def build(profile)
      PARTS.map { |part| profile[part] }.join(SEPARATOR)
    end

    # [device_id, vendor, mode], or nil if this is not a usable composite.
    # Caller distinguishes "nothing selected" from "malformed" by checking blank?
    # first - the two mean very different things at provision time.
    def parse(composite)
      return nil if blank?(composite)

      parts = composite.to_s.split(SEPARATOR, PARTS.length)
      return nil unless parts.length == PARTS.length
      return nil if parts.any? { |part| blank?(part) }

      parts
    end

    def label(profile)
      name = [profile['vendor_name'], profile['device_name']]
             .reject { |part| blank?(part) }
             .join(' ')
      name = "GPU #{profile['device_id']}" if name.empty?
      assignable = profile['assignable']
      assignable.nil? ? name : "#{name} (#{assignable} assignable)"
    end
  end
end
