import { Component } from '@angular/core';
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

  constructor(private auth: AuthService, private router: Router) {}

  login(): void {
    this.error = '';
    this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigate(['/validacion']),
      error: () => {
        this.error = 'Usuario o contraseña incorrectos.';
        this.loading = false;
      },
    });
  }
}
