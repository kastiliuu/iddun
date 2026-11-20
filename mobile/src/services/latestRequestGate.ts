/*
 * P-003 · Uma leitura assíncrona da lista só altera a tela se ainda
 * for a mais recente. O servidor continua sendo a fonte dos serviços.
 */
export function createLatestRequestGate() {
  let version = 0;
  return {
    begin(): number {
      version += 1;
      return version;
    },
    isCurrent(request: number): boolean {
      return request === version;
    },
    invalidate(request: number): void {
      if (request === version) version += 1;
    },
    // O blur invalida inclusive um retry feito após a leitura inicial.
    invalidateAll(): void {
      version += 1;
    },
  };
}
