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

    # Register the plugin with Foreman
    initializer 'foreman_nutanix.register_plugin', before: :finisher_hook do |_app|
      Foreman::Plugin.register :foreman_nutanix do
        requires_foreman '>= 3.14.0'
        register_gettext

        # Register the compute resource
        in_to_prepare do
          compute_resource(ForemanNutanix::GCE)
        end
      end
    end

    # Include extensions after all frameworks are loaded
    config.to_prepare do
      Rails.logger.info "ForemanNutanix: Loading extensions"
      
      # Include controller extensions
      require_dependency 'foreman_nutanix/api/v2/compute_resources_extensions'
      
      # Include API extensions
      ::Api::V2::ComputeResourcesController.include ForemanNutanix::Api::V2::ComputeResourcesExtensions
      ::Api::V2::ComputeResourcesController.include Foreman::Controller::Parameters::ComputeResourceExtension
      ::ComputeResourcesController.include Foreman::Controller::Parameters::ComputeResourceExtension
      
      # Include host extensions
      ::Host::Managed.include ForemanNutanix::HostManagedExtensions
      
      Rails.logger.info "ForemanNutanix: Extensions loaded successfully"
    rescue StandardError => e
      Rails.logger.warn "ForemanNutanix: Error loading extensions: #{e.message}"
      Rails.logger.warn e.backtrace.join("\n")
    end

    rake_tasks do
      Rake::Task['db:seed'].enhance do
        ForemanNutanix::Engine.load_seed
      end
    end
  end
end