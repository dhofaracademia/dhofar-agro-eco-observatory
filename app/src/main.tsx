import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./i18n";
import "./index.css";
import App from "./App";

const basename = (import.meta.env.BASE_URL || "/").replace(/\/$/, "") || "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={basename === "/" ? undefined : basename}>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
