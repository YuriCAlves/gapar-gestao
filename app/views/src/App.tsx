import { lazy, useEffect } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AvisosProvider } from "./contexts/AvisosContext";
import { FlagsProvider, RotaComFlag } from "./contexts/FlagsContext";
import { Layout } from "./components/Layout";
import { LayoutPublico } from "./components/LayoutPublico";
import { Carregando, EstadoErro } from "./components/Estados";
import { Botao } from "./components/Botao";
import LoginPage from "./pages/LoginPage";
import HojePage from "./pages/HojePage";
import AnimaisPage from "./pages/AnimaisPage";
import NaoEncontradaPage from "./pages/NaoEncontradaPage";

// Telas menos usadas no dia a dia e páginas públicas carregam só quando abertas (economia de dados móveis).
const AnimalNovoPage = lazy(() => import("./pages/AnimalNovoPage"));
const AnimalFichaPage = lazy(() => import("./pages/AnimalFichaPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const PrivacidadePage = lazy(() => import("./pages/publico/PrivacidadePage"));
const EmBrevePublicoPage = lazy(() => import("./pages/publico/EmBrevePublicoPage"));
const VitrinePage = lazy(() => import("./pages/publico/VitrinePage"));
const VitrineAnimalPage = lazy(() => import("./pages/publico/VitrineAnimalPage"));

function TelaCheia({ children }: { children: ReactNode }) {
  return <div className="grid min-h-dvh place-items-center px-4">{children}</div>;
}

/** Mantém o AuthProvider isolado às rotas internas, evitando chamadas a /auth/* nas rotas públicas. */
function AreaInterna() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

/** Só deixa passar quem tem sessão; guarda a rota pedida para voltar a ela depois de entrar. */
function RotaProtegida({ children, somenteAdministradora = false }: { children: ReactNode; somenteAdministradora?: boolean }) {
  const { situacao, ehAdministradora, verificarSessao, saiuPorVontade } = useAuth();
  const local = useLocation();

  if (situacao === "verificando") {
    return (
      <TelaCheia>
        <Carregando texto="Conferindo seu acesso..." />
      </TelaCheia>
    );
  }
  if (situacao === "indisponivel") {
    return (
      <TelaCheia>
        <div className="w-full max-w-md">
          <EstadoErro
            mensagem="Não foi possível falar com o sistema. Confira sua internet e tente de novo."
            aoTentarDeNovo={() => void verificarSessao()}
          />
        </div>
      </TelaCheia>
    );
  }
  if (situacao !== "autenticada") {
    // Quem saiu por vontade própria recomeça do início; quem perdeu a sessão volta para onde estava
    if (saiuPorVontade) return <Navigate to="/entrar" replace />;
    const destino = `${local.pathname}${local.search}`;
    return <Navigate to="/entrar" replace state={{ voltarPara: destino }} />;
  }
  if (somenteAdministradora && !ehAdministradora) {
    return (
      <div className="mx-auto max-w-md py-10 text-center">
        <h1 className="text-2xl">Área exclusiva da administradora</h1>
        <p className="mt-2">Esta parte do sistema só pode ser aberta pela administradora da GAPAR.</p>
        <Botao className="mt-5" onClick={() => window.history.back()}>
          Voltar
        </Botao>
      </div>
    );
  }
  return <>{children}</>;
}

/** Volta do Google cai em "/": se a pessoa tinha pedido outra tela antes de entrar, vai para ela. */
function Inicio() {
  let destino = "/hoje";
  try {
    destino = sessionStorage.getItem("gapar:voltarPara") || "/hoje";
  } catch {
    // sem armazenamento: segue para "Hoje"
  }
  useEffect(() => {
    try {
      sessionStorage.removeItem("gapar:voltarPara");
    } catch {
      // nada a limpar
    }
  }, []);
  return <Navigate to={destino} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <FlagsProvider>
        <AvisosProvider>
          <Routes>
            {/* Rotas públicas: fora do AuthContext, sem chamada a /auth/* */}
            <Route element={<LayoutPublico />}>
              <Route path="/privacidade" element={<PrivacidadePage />} />
              <Route path="/privacidade/*" element={<NaoEncontradaPage publica />} />
              <Route
                path="/adote"
                element={
                  <RotaComFlag flag="vitrine" publica>
                    <VitrinePage />
                  </RotaComFlag>
                }
              />
              <Route
                path="/adote/:slug"
                element={
                  <RotaComFlag flag="vitrine" publica>
                    <VitrineAnimalPage />
                  </RotaComFlag>
                }
              />
              <Route path="/adote/*" element={<NaoEncontradaPage publica />} />
              <Route path="/termo" element={<NaoEncontradaPage publica />} />
              <Route
                path="/termo/:token"
                element={
                  <RotaComFlag flag="termo_digital" publica>
                    <EmBrevePublicoPage titulo="Termo de adoção digital" />
                  </RotaComFlag>
                }
              />
              <Route path="/termo/*" element={<NaoEncontradaPage publica />} />
              <Route path="/carteira" element={<NaoEncontradaPage publica />} />
              <Route
                path="/carteira/:token"
                element={
                  <RotaComFlag flag="carteira" publica>
                    <EmBrevePublicoPage titulo="Carteira de vacinas" />
                  </RotaComFlag>
                }
              />
              <Route path="/carteira/*" element={<NaoEncontradaPage publica />} />
            </Route>

            {/* Rotas internas: com sessão Google + Whitelist */}
            <Route element={<AreaInterna />}>
              <Route path="/entrar" element={<LoginPage />} />
              <Route
                element={
                  <RotaProtegida>
                    <Layout />
                  </RotaProtegida>
                }
              >
                <Route path="/" element={<Inicio />} />
                <Route path="/hoje" element={<HojePage />} />
                <Route path="/animais" element={<AnimaisPage />} />
                <Route path="/animais/novo" element={<AnimalNovoPage />} />
                <Route path="/animais/:id" element={<AnimalFichaPage />} />
                <Route
                  path="/admin"
                  element={
                    <RotaProtegida somenteAdministradora>
                      <AdminPage />
                    </RotaProtegida>
                  }
                />
                <Route path="*" element={<NaoEncontradaPage />} />
              </Route>
            </Route>
          </Routes>
        </AvisosProvider>
      </FlagsProvider>
    </BrowserRouter>
  );
}
