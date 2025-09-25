module ForemanNutanixshim
  class Nutanix < ComputeResource

    # Display name in the UI
    def self.model_name
      ActiveModel::Name.new(self, nil, "Nutanix")
    end

    SETTINGS = [
      { name: :api_url, type: :string, label: "Nutanix API URL" },
      { name: :username, type: :string },
      { name: :password, type: :password }
    ].freeze

    def self.settings
      SETTINGS
    end

    def create_host(host, options = {})
    end

    def delete_host(host)
    end

  end
end
