/// <reference types="svelte" />
/// <reference types="vite/client" />
export {};

declare global {
  interface Window {
    pywebview: {
        api: {
          [key: string]: (...args: any[]) => any;
        };
      };
      SetValue:any;
      GetValue:any;
  }
}