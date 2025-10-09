module ForemanNutanix
  module Api
    module V2
      module ApipieExtensions
        extend Apipie::DSL::Concern

        update_api(:create, :update) do
          param :compute_resource, Hash do
            param :key_path, String, desc: N_('Certificate path, for GCE only')
            param :zone, String, desc: N_('Zone, for GCE only')
            param :project, String, desc: N_('Deprecated, project is automatically loaded from the JSON file. For GCE only')
            param :email, String, desc: N_('Deprecated, email is automatically loaded from the JSON file. For GCE only')
          end
        end
      end
    end
  end
end
