import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export type RolUsuario = 'broker' | 'suscriptor';

interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  rol: RolUsuario;
  nombre: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  // URL relativa → pasa por el proxy de Angular (proxy.conf.json → localhost:8000)
  private readonly API = '/api/v1/auth';
  private readonly TOKEN_KEY = 'poc_token';
  private readonly USER_KEY = 'poc_user';
  private readonly ROL_KEY = 'poc_rol';
  private readonly NOMBRE_KEY = 'poc_nombre';

  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.API}/login`, { username, password }).pipe(
      tap(res => {
        localStorage.setItem(this.TOKEN_KEY, res.access_token);
        localStorage.setItem(this.USER_KEY, res.username);
        localStorage.setItem(this.ROL_KEY, res.rol);
        localStorage.setItem(this.NOMBRE_KEY, res.nombre || res.username);
      }),
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    localStorage.removeItem(this.ROL_KEY);
    localStorage.removeItem(this.NOMBRE_KEY);
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem(this.TOKEN_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getUsername(): string {
    return localStorage.getItem(this.USER_KEY) ?? '';
  }

  getRol(): RolUsuario | null {
    return (localStorage.getItem(this.ROL_KEY) as RolUsuario | null) ?? null;
  }

  getNombre(): string {
    return localStorage.getItem(this.NOMBRE_KEY) ?? this.getUsername();
  }
}