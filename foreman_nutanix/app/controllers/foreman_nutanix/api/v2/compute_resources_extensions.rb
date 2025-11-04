module ForemanNutanix
  module Api
    module V2
      module HostsController
        extend ActiveSupport::Concern

        included do
          # https://github.com/theforeman/foreman/blob/develop/app/controllers/api/v2/hosts_controller.rb
          def power_status
            # NOTE: params.id is the FQDN
            Rails.logger.info "HostsController::power_status #{params[:id]}"
            render json: { id: @host.id, state: 'on', title: 'On', statusText: 'Powered On' }
          end
        end
      end

      module ComputeResourcesExtensions
        extend ActiveSupport::Concern

        # rubocop:disable Rails/LexicallyScopedActionFilter
        included do
          before_action :read_key, only: [:create]
          before_action :deprecated_params, only: [:create]
        end
        # rubocop:enable Rails/LexicallyScopedActionFilter

        private

        def read_key
          return unless compute_resource_params['provider'] == 'GCE'
          params[:compute_resource][:password] = File.read(params['compute_resource'].delete('key_path'))
        end

        def deprecated_params
          return unless compute_resource_params['provider'] == 'GCE'

          if compute_resource_params['email']
            msg = _('The email parameter is deprecated, value is automatically loaded from the JSON file')
            Foreman::Deprecation.api_deprecation_warning(msg)
          end

          return unless compute_resource_params['project']
          msg = _('The project parameter is deprecated, value is automatically loaded from the JSON file')
          Foreman::Deprecation.api_deprecation_warning(msg)
        end
      end
    end
  end
end
