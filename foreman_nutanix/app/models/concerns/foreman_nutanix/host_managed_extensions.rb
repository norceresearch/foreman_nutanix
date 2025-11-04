module ForemanNutanix
  module HostManagedExtensions
    def ip_addresses
      vm&.ip_addresses || ['127.0.055', '127.0.056']
    end

    def vm_ip_address
      Rails.logger.info 'Calling vm ip address'
      return '127.0.0.5'
      vm&.vm_ip_address
    end
  end
end
