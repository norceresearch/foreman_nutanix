module ForemanNutanix
  module Api
    module V2
      module HostsControllerExtensions
        extend ActiveSupport::Concern

        included do
          # Prepend to override the power_status method
          prepend PowerStatusOverride
        end

        module PowerStatusOverride
          def power_status
            Rails.logger.info "=== NUTANIX: HostsControllerExtensions::power_status called ==="

            # Check if this host uses a Nutanix compute resource
            if @host&.compute_resource.is_a?(ForemanNutanix::Nutanix)
              Rails.logger.info "=== NUTANIX: Host #{@host.name} uses Nutanix compute resource ==="

              # Get the VM and its actual power state
              vm = @host.compute_resource.find_vm_by_uuid(@host.uuid)
              if vm
                state = vm.state
                Rails.logger.info "=== NUTANIX: VM state is '#{state}' ==="

                # Map to Foreman's expected format
                case state
                when 'running'
                  render json: { id: @host.id, state: 'on', title: 'On', statusText: 'Powered On' }
                when 'stopped'
                  render json: { id: @host.id, state: 'off', title: 'Off', statusText: 'Powered Off' }
                when 'paused'
                  render json: { id: @host.id, state: 'paused', title: 'Paused', statusText: 'Paused' }
                else
                  render json: { id: @host.id, state: 'na', title: 'N/A', statusText: 'Unknown' }
                end
              else
                Rails.logger.warn "=== NUTANIX: VM not found for host #{@host.name} ==="
                render json: { id: @host.id, state: 'na', title: 'N/A', statusText: 'VM Not Found' }
              end
            else
              # Fall back to default behavior for non-Nutanix hosts
              super
            end
          end
        end
      end
    end
  end
end
