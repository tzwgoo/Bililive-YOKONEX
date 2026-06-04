export function useLocalDraft<TValue>(storageKey: string, defaultValue: TValue) {
  const load = (): TValue => {
    const rawValue = window.localStorage.getItem(storageKey);
    if (!rawValue) {
      return defaultValue;
    }
    try {
      return JSON.parse(rawValue) as TValue;
    } catch {
      return defaultValue;
    }
  };

  const save = (value: TValue) => {
    window.localStorage.setItem(storageKey, JSON.stringify(value));
  };

  const clear = () => {
    window.localStorage.removeItem(storageKey);
  };

  return {
    load,
    save,
    clear,
  };
}
