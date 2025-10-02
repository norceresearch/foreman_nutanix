module ForemanNutanixshim

  class Nutanix < ComputeResource

    attr_accessor :endpoint, :cluster

    def available_clusters
      # TODO: config for nutanix shim server
      uri = URI("http://localhost:8000/api/v1/clustermgmt/list-clusters")
      response = Net::HTTP.get_response(uri)
      data = JSON.parse(response.body)

      # Convert array of hashmaps to structs for templating
      clusters = data.map do |cluster|
        cluster[:expanded_name] = "#{cluster['name']} (#{cluster['arch']})"
        OpenStruct.new(cluster)
      end

      clusters
    end

    def self.provider_friendly_name
      "Nutanix"
    end

    def self.model_name
      ActiveModel::Name.new(self, nil, "Nutanix")
    end

    def create_host(host, options = {})
      Rails.logger.debug "host=#{host} - options=#{options}"
    end

    def delete_host(host)
      Rails.logger.debug "host=#{host}"
    end

  end
end
