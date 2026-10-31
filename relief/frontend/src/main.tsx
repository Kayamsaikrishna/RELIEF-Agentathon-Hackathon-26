import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@fontsource-variable/plus-jakarta-sans";
import "./styles/base.css";
import "./styles/landing.css";
import "./styles/app.css";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ToastProvider } from "./components/ui";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter><AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider></BrowserRouter>
  </React.StrictMode>,
);
