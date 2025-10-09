module ForemanNutanix
  module Api
    module V2
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
