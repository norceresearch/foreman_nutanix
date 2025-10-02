module ForemanNutanixshim

  class Nutanix < ComputeResource

    attr_accessor :endpoint, :cluster

    def available_clusters
      # TODO: config for nutanix shim server
      uri = URI("http://localhost:8000/api/v1/clustermgmt/list-clusters")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)
      Rails.logger.debug "#{data}"

      # Convert array of hashmaps to structs for templating
      clusters = data.map do |cluster|
        cluster[:expanded_name] = "#{cluster['name']} (#{cluster['arch']})"
        OpenStruct.new(cluster)
      end
      Rails.logger.debug "#{clusters}"

      clusters
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
