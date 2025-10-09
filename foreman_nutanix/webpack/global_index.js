import { registerRoutes } from "foremanReact/routes/RoutingService";
import Routes from "./src/Router/routes";
import { registerLegacy } from "./legacy";

registerRoutes("ForemanNutanix", Routes);
registerLegacy();
