import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ReporteValidacion, ResultadoValidacion } from '../../services/validacion';

@Component({
  selector: 'app-reporte',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './reporte.html',
  styleUrl: './reporte.scss',
})
export class ReporteComponent implements OnInit {
  reporte: ReporteValidacion | null = null;
  filtro: 'todos' | 'error' | 'advertencia' = 'todos';

  constructor(private router: Router) {}

  ngOnInit(): void {
    const raw = sessionStorage.getItem('ultimo_reporte');
    if (raw) {
      this.reporte = JSON.parse(raw) as ReporteValidacion;
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  get resultadosFiltrados(): ResultadoValidacion[] {
    if (!this.reporte) return [];
    if (this.filtro === 'todos') return this.reporte.resultados;
    return this.reporte.resultados.filter(r => r.tipo === this.filtro);
  }

  get errores(): ResultadoValidacion[] {
    return this.reporte?.resultados.filter(r => r.tipo === 'error') ?? [];
  }

  get advertencias(): ResultadoValidacion[] {
    return this.reporte?.resultados.filter(r => r.tipo === 'advertencia') ?? [];
  }

  setFiltro(f: 'todos' | 'error' | 'advertencia'): void {
    this.filtro = f;
  }

  nuevaValidacion(): void {
    sessionStorage.removeItem('ultimo_reporte');
    this.router.navigate(['/dashboard']);
  }
}
