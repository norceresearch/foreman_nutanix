module ForemanNutanix
  module Api
    module V2
      module ComputeResourcesExtensions
        extend ActiveSupport::Concern

        included do
          before_action :read_key, only: [:create]
          before_action :deprecated_params, only: [:create]
        end

        private

        def read_key
          return unless compute_resource_params['provider'] == 'Nutanix'
          # Handle key file reading if needed
          Rails.logger.info "ForemanNutanix: Reading key for Nutanix provider"
        end

        def deprecated_params
          return unless compute_resource_params['provider'] == 'Nutanix'

          # Handle deprecated parameters
          Rails.logger.info "ForemanNutanix: Checking deprecated params for Nutanix provider"
        end
      end
    end
  end
end