module Foreman
  module Controller
    module Parameters
      module ComputeResourceExtension
        extend ActiveSupport::Concern

        class_methods do
          def compute_resource_params_filter
            super.tap do |filter|
              filter.permit :key_path, :zone
            end
          end
        end
      end
    end
  end
end
