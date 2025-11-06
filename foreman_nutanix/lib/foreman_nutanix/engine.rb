module ForemanNutanix
  class Engine < ::Rails::Engine
    isolate_namespace ForemanNutanix
    engine_name 'foreman_nutanix'

    # Add any db migrations
    initializer 'foreman_nutanix.load_app_instance_data' do |app|
      ForemanNutanix::Engine.paths['db/migrate'].existent.each do |path|
        app.config.paths['db/migrate'] << path
      end
    end

    initializer 'foreman_nutanix.register_plugin', before: :finisher_hook do |_app|
      Foreman::Plugin.register :foreman_nutanix do
        requires_foreman '>= 3.13.0'
        register_gettext

        in_to_prepare do
          compute_resource(ForemanNutanix::GCE)
        end
      end
    end

    # Include concerns in this config.to_prepare block
    config.to_prepare do
      ::Host::Managed.include ForemanNutanix::HostManagedExtensions

      ::Api::V2::ComputeResourcesController.include ForemanNutanix::Api::V2::ComputeResourcesExtensions
      ::Api::V2::ComputeResourcesController.include Foreman::Controller::Parameters::ComputeResourceExtension

      ::ComputeResourcesController.include Foreman::Controller::Parameters::ComputeResourceExtension

      ::Api::V2::HostsController.include ForemanNutanix::Api::V2::HostsController
      # Nutanix::Cloud::Compute::V1::AttachedDisk.include NutanixExtensions::AttachedDisk
    rescue StandardError => e
      Rails.logger.warn "ForemanNutanix: skipping engine hook (#{e})"
    end

    rake_tasks do
      Rake::Task['db:seed'].enhance do
        ForemanNutanix::Engine.load_seed
      end
    end
  end
end
