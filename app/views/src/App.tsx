import { lazy, Suspense, useEffect } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AvisosProvider } from "./contexts/AvisosContext";
import { Layout } from "./components/Layout";
import { Carregando, EstadoErro } from "./components/Estados";
import { Botao } from "./components/Botao";
import LoginPage from "./pages/LoginPage";
import HojePage from "./pages/HojePage";
import AnimaisPage from "./pages/AnimaisPage";
import NaoEncontradaPage from "./pages/NaoEncontradaPage";

// Telas menos usadas no dia a dia carregam só quando abertas (economia de dados móveis).
const AnimalNovoPage = lazy(() => import("./pages/AnimalNovoPage"));
const AnimalFichaPage = lazy(() => import("./pages/AnimalFichaPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

function TelaCheia({ children }: { children: ReactNode }) {
  return <div className="grid min-h-dvh place-items-center px-4">{children}</div>;
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
      <AuthProvider>
        <AvisosProvider>
          <Suspense
            fallback={
              <TelaCheia>
                <Carregando />
              </TelaCheia>
            }
          >
            <Routes>
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
            </Routes>
          </Suspense>
        </AvisosProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
