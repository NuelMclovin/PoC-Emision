import { Component } from '@angular/core';
import { GmmProcesoComponent } from '../gmm-proceso/gmm-proceso';

@Component({
  selector: 'app-nueva-gmm',
  standalone: true,
  imports: [GmmProcesoComponent],
  template: '<app-gmm-proceso tipoAccion="nueva"></app-gmm-proceso>',
})
export class NuevaGmmComponent {}