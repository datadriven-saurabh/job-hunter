// Keep provider tokens and error descriptions out of application URLs and logs.
export function confirmationError(url:string){
 const parsed=new URL(url);
 const fragment=new URLSearchParams(parsed.hash.slice(1));
 const code=fragment.get('error_code')||parsed.searchParams.get('error_code');
 const error=fragment.get('error')||parsed.searchParams.get('error');
 if(!code&&!error)return '';
 return code==='otp_expired'?'expired':'invalid';
}
export function confirmationMessage(reason:string){
 return reason==='expired'
  ?'This confirmation link has expired or was already used. If you already verified your email, sign in below. Otherwise, request a new confirmation email.'
  :'We could not complete email confirmation. Sign in if your email is already verified, or request a new confirmation email.';
}
export function authErrorMessage(error:{message:string;status?:number;code?:string}){
 if(error.status===429||error.code==='over_email_send_rate_limit')return 'Email sending is temporarily rate limited. Please wait before requesting another confirmation email.';
 return error.message;
}
