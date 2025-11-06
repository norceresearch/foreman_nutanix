module ForemanNutanix
  module HostManagedExtensions
    extend ActiveSupport::Concern

    included do
      # Add any callbacks or validations here if needed
    end

    def ip_addresses
      Rails.logger.info "=== NUTANIX: HOST::ip_addresses called, vm: #{vm} ==="
      vm&.ip_addresses || ['192.168.1.100', '10.0.0.100']
    end

    def vm_ip_address
      Rails.logger.info "=== NUTANIX: HOST::vm_ip_address called, vm: #{vm} ==="
      vm&.vm_ip_address || '192.168.1.100'
    end

    # Override provisioning methods to add debugging
    def provision_method
      Rails.logger.info "=== NUTANIX: HOST::provision_method called ==="
      super
    end

    def build?
      Rails.logger.info "=== NUTANIX: HOST::build? called, build: #{super} ==="
      super
    end
  end
end