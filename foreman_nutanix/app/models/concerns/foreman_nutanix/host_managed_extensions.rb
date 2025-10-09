module ForemanNutanix
  module HostManagedExtensions
    def ip_addresses
      vm&.ip_addresses || []
    end

    def vm_ip_address
      vm&.vm_ip_address
    end
  end
end
