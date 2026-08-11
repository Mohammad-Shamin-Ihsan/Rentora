import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { LucideAngularModule, Star, BadgeCheck } from 'lucide-angular';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(),
    importProvidersFrom(
      LucideAngularModule.pick({ Star, BadgeCheck })
    ),
  ],
};
