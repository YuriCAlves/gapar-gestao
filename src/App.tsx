import { useEffect, useState } from "react";

// Placeholder do Checkpoint 1: confirma a ponte SPA -> Flask. Rotas reais entram no Checkpoint 4.
export default function App() {
  const [status, setStatus] = useState("verificando...");

  useEffect(() => {
    fetch("/auth/status")
      .then((r) => r.json())
      .then((d) => setStatus(d.autenticado ? "sessão ativa" : "API online, sem sessão"))
      .catch(() => setStatus("API indisponível"));
  }, []);

  return (
    <main className="min-h-screen grid place-items-center bg-amber-50 text-stone-800">
      <div className="text-center">
        <h1 className="text-3xl font-bold">GAPAR Gestão</h1>
        <p className="mt-2 text-stone-600">Backend: {status}</p>
      </div>
    </main>
  );
}
