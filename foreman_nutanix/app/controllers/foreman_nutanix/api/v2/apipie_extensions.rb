module ForemanNutanix
  module Api
    module V2
      module ApipieExtensions
        extend Apipie::DSL::Concern

        update_api(:create, :update) do
          param :compute_resource, Hash do
            param :cluster, String, desc: N_('Nutanix cluster UUID')
            param :zone, String, desc: N_('Zone/availability zone')
          end
        end
      end
    end
  end
end
