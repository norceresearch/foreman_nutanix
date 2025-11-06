module ForemanNutanix
  class NutanixComputeAdapter
    def initialize(args = {})
      Rails.logger.info "NutanixComputeAdapter::initialize args=#{args}"
    end

    def servers
      ForemanNutanix::NutanixCompute
    end

    def create_server(attrs = {})
      Rails.logger.info "NutanixComputeAdapter::create_server attrs=#{attrs}"
    end

    def flavors
      Rails.logger.info 'NutanixComputeAdapter::flavors'
      %i[flavor1foo]
    end

    def networks
      Rails.logger.info 'NutanixComputeAdapter::networks'
      ['SomeNetwork']
    end

    def project_id
      'project-id-here'
    end
  end
end
