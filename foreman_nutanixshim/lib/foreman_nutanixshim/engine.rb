module ForemanNutanixshim
  class Engine < ::Rails::Engine
    isolate_namespace ForemanNutanixshim
    engine_name 'foreman_nutanixshim'

    # Add any db migrations
    initializer 'foreman_nutanixshim.load_app_instance_data' do |app|
      ForemanNutanixshim::Engine.paths['db/migrate'].existent.each do |path|
        app.config.paths['db/migrate'] << path
      end
    end

    initializer 'foreman_nutanixshim.register_plugin', :before => :finisher_hook do |app|
      app.reloader.to_prepare do
        Foreman::Plugin.register :foreman_nutanixshim do
          requires_foreman '>= 3.14.0'
          register_gettext

          compute_resource ForemanNutanixshim::Nutanix

          # Add Global files for extending foreman-core components and routes
          register_global_js_file 'global'

          # Add permissions
          security_block :foreman_nutanixshim do
            permission :view_foreman_nutanixshim, { :'foreman_nutanixshim/example' => [:new_action],
                                                        :react => [:index] }
          end

          # Add a new role called 'Discovery' if it doesn't exist
          role 'ForemanNutanixshim', [:view_foreman_nutanixshim]

          # add menu entry
          sub_menu :top_menu, :plugin_template, icon: 'pficon pficon-enterprise', caption: N_('Nutanix Shim'), after: :hosts_menu do
            menu :top_menu, :welcome, caption: N_('Welcome Page'), engine: ForemanNutanixshim::Engine
            menu :top_menu, :new_action, caption: N_('New Action'), engine: ForemanNutanixshim::Engine
          end

          # add dashboard widget
          widget 'foreman_nutanixshim_widget', name: N_('Foreman plugin template widget'), sizex: 4, sizey: 1
        end
      end
    end

    # Include concerns in this config.to_prepare block
    config.to_prepare do
      Host::Managed.include ForemanNutanixshim::HostExtensions
      HostsHelper.include ForemanNutanixshim::HostsHelperExtensions
    rescue StandardError => e
      Rails.logger.warn "ForemanNutanixshim: skipping engine hook (#{e})"
    end

    rake_tasks do
      Rake::Task['db:seed'].enhance do
        ForemanNutanixshim::Engine.load_seed
      end
    end
  end
end
