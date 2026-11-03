import { NavLink, Route, Routes } from "react-router-dom";
import AdminPage from "./pages/AdminPage";
import CapturePage from "./pages/CapturePage";
import IdentifyPage from "./pages/IdentifyPage";

export default function App() {
  return (
    <div className="app-shell">
      <header>
        <h1 className="brand">Analiza dynamiki pisania</h1>
        <p className="lede">
          Badanie charakteru wprowadzania tekstu na podstawie mikroczasów
          naciskania i zwalniania klawiszy. Dane są zbierane wyłącznie w ramach
          sesji badawczej.
        </p>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
            Sesja uczestnika
          </NavLink>
          <NavLink to="/identify" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Identyfikuj
          </NavLink>
          <NavLink to="/admin" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Panel badacza
          </NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<CapturePage />} />
        <Route path="/identify" element={<IdentifyPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </div>
  );
}
