import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  // URL relativa → pasa por el proxy de Angular (proxy.conf.json → localhost:8000)
  private readonly API = '/api/v1/auth';
  private readonly TOKEN_KEY = 'poc_token';
  private readonly USER_KEY = 'poc_user';

  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.API}/login`, { username, password }).pipe(
      tap(res => {
        localStorage.setItem(this.TOKEN_KEY, res.access_token);
        localStorage.setItem(this.USER_KEY, res.username);
      }),
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
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
}
