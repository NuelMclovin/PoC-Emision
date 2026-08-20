import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';
  loading = false;

  constructor(
    private auth: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  login(): void {
    this.error = '';
    this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: () => {
        if (this.auth.getRol() !== 'broker') {
          this.auth.logout();
          this.error = 'Esta cuenta no tiene acceso al portal de bróker.';
          this.loading = false;
          this.cdr.markForCheck();
          return;
        }
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.error = 'Usuario o contraseña incorrectos.';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }
}