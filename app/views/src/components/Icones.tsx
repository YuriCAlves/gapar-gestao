import type { ReactNode, SVGProps } from "react";

// Ícones do app, desenhados em linha (sem biblioteca externa). São sempre decorativos:
// o nome acessível vem do texto ou do aria-label do elemento que os contém.

type PropsDoIcone = SVGProps<SVGSVGElement> & { tamanho?: number };

function Base({ tamanho = 24, children, ...resto }: PropsDoIcone & { children: ReactNode }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...resto}
    >
      {children}
    </svg>
  );
}

export function IconePata({ tamanho = 24, ...resto }: PropsDoIcone) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false" {...resto}>
      <ellipse cx="6.2" cy="10.2" rx="2" ry="2.7" />
      <ellipse cx="12" cy="7.4" rx="2" ry="2.7" />
      <ellipse cx="17.8" cy="10.2" rx="2" ry="2.7" />
      <path d="M12 12c-3.100 0-5.400 2.600-5.400 5 0 1.700 1.200 2.500 2.700 2.500 1.100 0 1.700-.5 2.700-.5s1.600.5 2.700.5c1.500 0 2.700-.8 2.700-2.500 0-2.400-2.300-5-5.400-5z" />
    </svg>
  );
}

export function IconeHoje(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="3.5" y="5" width="17" height="15.500" rx="3" />
      <path d="M8 3v4M16 3v4M3.5 10h17" />
      <path d="m9 15 2 2 4-4" />
    </Base>
  );
}

export function IconeMais(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 5v14M5 12h14" />
    </Base>
  );
}

export function IconeAdmin(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 3 5 6v5.500c0 4.300 2.900 7.700 7 9.500 4.100-1.800 7-5.200 7-9.500V6l-7-3z" />
      <path d="m9.200 12 2 2 3.600-4" />
    </Base>
  );
}

export function IconeSair(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M10 4H6.500A2.500 2.500 0 0 0 4 6.500v11A2.500 2.500 0 0 0 6.500 20H10" />
      <path d="M15 8l4 4-4 4M19 12H9.500" />
    </Base>
  );
}

export function IconeBusca(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <circle cx="11" cy="11" r="6.500" />
      <path d="m20 20-4.200-4.200" />
    </Base>
  );
}

export function IconeFiltro(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M4 7h16M7 12h10M10 17h4" />
    </Base>
  );
}

export function IconeCerto(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12.300 2.700 2.700L16 9.500" />
    </Base>
  );
}

export function IconeAlerta(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 4 2.800 19.500h18.400L12 4z" />
      <path d="M12 10v4.500M12 17.200v.100" />
    </Base>
  );
}

export function IconeInfo(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.500M12 7.700v.100" />
    </Base>
  );
}

export function IconeFechar(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Base>
  );
}

export function IconeCamera(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M4 8.500A2.500 2.500 0 0 1 6.500 6h1.300l1.400-2h5.600l1.400 2h1.300A2.500 2.500 0 0 1 20 8.500v8A2.500 2.500 0 0 1 17.500 19h-11A2.500 2.500 0 0 1 4 16.500v-8z" />
      <circle cx="12" cy="12.500" r="3.200" />
    </Base>
  );
}

export function IconeVoltar(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </Base>
  );
}

export function IconeAvancar(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="m9 6 6 6-6 6" />
    </Base>
  );
}

export function IconeRelogio(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Base>
  );
}

export function IconeVacina(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="m17 3 4 4M19 5l-3.500 3.500M13 6l5 5M14.500 7.500 6 16v2h2l8.500-8.500M4 20l2-2M9.500 12.500l1.500 1.500" />
    </Base>
  );
}

export function IconeRemedio(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="2.700" y="8.500" width="18.600" height="7" rx="3.500" transform="rotate(-45 12 12)" />
      <path d="m9 9 6 6" />
    </Base>
  );
}

export function IconeCoracao(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 20s-7-4.300-7-9.500A4 4 0 0 1 12 8a4 4 0 0 1 7 2.500c0 5.200-7 9.500-7 9.500z" />
    </Base>
  );
}

export function IconeCadeado(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="5" y="10.500" width="14" height="9.500" rx="2.500" />
      <path d="M8 10.500V8a4 4 0 0 1 8 0v2.500" />
    </Base>
  );
}

export function IconeLapis(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M4 20h4L19 9l-4-4L4 16v4zM13.500 6.500l4 4" />
    </Base>
  );
}

export function IconeBaixar(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 4v11M7.500 11l4.500 4.500 4.500-4.500M5 20h14" />
    </Base>
  );
}

export function IconeLixeira(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M4 7h16M9.500 7V4.500h5V7M6.500 7l.8 12.500h9.400L17.500 7M10 11v5M14 11v5" />
    </Base>
  );
}

export function IconeLocal(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M12 21s-6.500-5.600-6.500-11a6.500 6.500 0 0 1 13 0c0 5.400-6.500 11-6.500 11z" />
      <circle cx="12" cy="10" r="2.300" />
    </Base>
  );
}

export function IconeProntuario(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="5" y="4" width="14" height="17" rx="2.500" />
      <path d="M9 4V3h6v1M12 10v6M9 13h6" />
    </Base>
  );
}

export function IconePessoa(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <circle cx="12" cy="8.500" r="3.500" />
      <path d="M5 20c.6-3.600 3.400-5.500 7-5.500s6.400 1.900 7 5.500" />
    </Base>
  );
}

export function IconeCalendario(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="3.500" y="5" width="17" height="15.500" rx="3" />
      <path d="M8 3v4M16 3v4M3.500 10h17" />
    </Base>
  );
}

export function IconeAtualizar(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M20 11a8 8 0 0 0-14.300-4M4 4v3.500h3.500M4 13a8 8 0 0 0 14.300 4M20 20v-3.500h-3.500" />
    </Base>
  );
}

export function IconeMenu(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Base>
  );
}

export function IconeQrCode(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <rect x="14" y="4" width="6" height="6" rx="1" />
      <rect x="4" y="14" width="6" height="6" rx="1" />
      <path d="M14 14h2v2h-2zM18 14h2v2h-2zM14 18h2v2h-2zM18 18h2v2h-2z" />
    </Base>
  );
}

export function IconeImprimir(props: PropsDoIcone) {
  return (
    <Base {...props}>
      <path d="M7 8V4h10v4" />
      <rect x="4" y="8" width="16" height="8" rx="2" />
      <path d="M7 14h10v6H7z" />
    </Base>
  );
}
