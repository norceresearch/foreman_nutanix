module ForemanNutanixshim

  # Struct for selected cluster
  NutanixCluster = Struct.new(:id, :name)

  class Nutanix < ComputeResource

    attr_accessor :endpoint, :cluster

    # TODO: Impl discovering available clusters from django app
    def available_clusters
      [
        NutanixCluster.new("a", "Cluster A"),
        NutanixCluster.new("b", "Cluster B")
      ]
    end

    def self.provider_friendly_name
      "Nutanix"
    end

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
