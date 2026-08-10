import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
  AbstractControl,
  ValidationErrors
} from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

// Custom validator: confirm password must match password
function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password        = control.get('password');
  const confirmPassword = control.get('confirm_password');

  if (!password || !confirmPassword) return null;

  if (password.value !== confirmPassword.value) {
    confirmPassword.setErrors({ mismatch: true });
    return { mismatch: true };
  } else {
    // Clear mismatch error if passwords now match
    const errors = { ...confirmPassword.errors };
    delete errors['mismatch'];
    confirmPassword.setErrors(Object.keys(errors).length ? errors : null);
    return null;
  }
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrls: ['./register.css']
})
export class Register{

  form: FormGroup;
  isLoading    = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.form = this.fb.group(
      {
        full_name:        ['', [Validators.required, Validators.minLength(2)]],
        email:            ['', [Validators.required, Validators.email]],
        password:         ['', [Validators.required, Validators.minLength(6)]],
        confirm_password: ['', [Validators.required]],
        role:             ['customer', [Validators.required]]
      },
      { validators: passwordMatchValidator }
    );
  }

  get full_name()        { return this.form.get('full_name')!; }
  get email()            { return this.form.get('email')!; }
  get password()         { return this.form.get('password')!; }
  get confirm_password() { return this.form.get('confirm_password')!; }
  get role()             { return this.form.get('role')!; }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading     = true;
    this.errorMessage  = '';
    this.successMessage = '';

    const { full_name, email, password, role } = this.form.value;

    this.authService.register({ full_name, email, password, role }).subscribe({
      next: () => {
        this.isLoading = false;
        // Redirect to home after successful registration
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage =
          err.error?.detail || 'Registration failed. Please try again.';
      }
    });
  }
}