module ForemanNutanix
  module HostManagedExtensions
    extend ActiveSupport::Concern

    included do
    end

    def ip_addresses
      Rails.logger.info "=== NUTANIX: HOST::ip_addresses called, vm: #{vm.inspect} ==="
      vm&.ip_addresses || ['192.168.1.100', '10.0.0.100']
    end

    # TODO: Hard-coded should probably be removed
    def vm_ip_address
      Rails.logger.info "=== NUTANIX: HOST::vm_ip_address called, vm: #{vm.inspect} ==="
      vm&.vm_ip_address || '192.168.1.100'
    end

    # Override provisioning methods to add debugging
    def provision_method
      Rails.logger.info '=== NUTANIX: HOST::provision_method called ==='
      super
    end

    def build?
      Rails.logger.info "=== NUTANIX: HOST::build? called, build: #{super} ==="
      super
    end

    # Override vm method to add debugging
    def vm
      Rails.logger.info "=== NUTANIX: HOST::vm called, compute_resource: #{compute_resource.inspect} ==="
      Rails.logger.info "=== NUTANIX: HOST::vm uuid: #{uuid} ==="
      super
    end
  end
end

