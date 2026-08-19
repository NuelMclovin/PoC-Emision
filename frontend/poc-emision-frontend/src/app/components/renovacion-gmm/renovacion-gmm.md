import { Component } from '@angular/core';
import { GmmProcesoComponent } from '../gmm-proceso/gmm-proceso';

@Component({
  selector: 'app-renovacion-gmm',
  standalone: true,
  imports: [GmmProcesoComponent],
  template: '<app-gmm-proceso tipoAccion="renovacion"></app-gmm-proceso>',
})
export class RenovacionGmmComponent {}