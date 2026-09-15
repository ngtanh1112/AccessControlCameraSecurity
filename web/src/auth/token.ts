const TOKEN_KEY = "access_control_camera_security.jwt";

export const readToken = (): string | null => window.localStorage.getItem(TOKEN_KEY);
export const saveToken = (token: string): void => window.localStorage.setItem(TOKEN_KEY, token);
export const clearToken = (): void => window.localStorage.removeItem(TOKEN_KEY);
