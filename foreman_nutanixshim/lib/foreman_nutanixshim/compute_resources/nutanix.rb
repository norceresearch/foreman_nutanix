# lib/foreman_nutanixshim/compute_resources/nutanix.rb
module ForemanNutanixshim
  class Nutanix < ::ComputeResource

    # Display name in the UI
    def self.model_name
      ActiveModel::Name.new(self, nil, "Nutanix")
    end

    # List of settings the user can configure in the UI
    SETTINGS = [
      { name: :api_url, type: :string, label: "Nutanix API URL" },
      { name: :username, type: :string },
      { name: :password, type: :password }
    ].freeze

    # Required by Foreman to expose settings
    def self.settings
      SETTINGS
    end

    # Optional: implement actual provisioning API call
    def create_host(host, options = {})
      # In your case, forward to your API shim
    end

    def delete_host(host)
      # Delete host via API shim
    end

    # ...implement other CRUD actions: start, stop, etc.
  end
end
