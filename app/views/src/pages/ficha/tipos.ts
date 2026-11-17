import type { FichaAnimal } from "../../types";

/** O que toda aba da ficha recebe. */
export interface PropsDaAba {
  ficha: FichaAnimal;
  /** RN05: adotado ou óbito. Nada pode ser alterado, só consultado. */
  congelado: boolean;
  /** Busca a ficha de novo depois de uma alteração. */
  aoAtualizar: () => void;
}
