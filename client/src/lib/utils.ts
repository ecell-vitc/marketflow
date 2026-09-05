export const SERVER_HOST = import.meta.env.VITE_SERVER_HOST as string

const isLocalHost = /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(SERVER_HOST)
export const SERVER_HTTP_PROTOCOL = isLocalHost ? 'http' : 'https'
export const SERVER_WS_PROTOCOL = isLocalHost ? 'ws' : 'wss'

export const makeRequest = async(
    path: string,
    method: RequestInit['method'],
    data?: Record<string, unknown>,
    includeAuth: boolean = false,
    tokenKey: string = 'token'
) => {
    const token = localStorage.getItem(tokenKey)
    if (includeAuth && !token) return { "detail": { "message": "You are not logged in" } };

    const res = await fetch(`${SERVER_HTTP_PROTOCOL}://${SERVER_HOST}/${path}`, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            ...(includeAuth && token ? { 'user-token': token } : {})
        },
        ...(data ? { body: JSON.stringify(data) } : {})
    })

    const r = await res.json()
    return r ?? { "detail": { "message": "Request failed" } }
}


export const getFormData = async (form: HTMLFormElement) => {
    const res: Record<string, string> = {}
    form.querySelectorAll('input').forEach((input) => {
        res[input.name] = input.value
    })
    return res
}


export const showMessage = (message: string, isError?: boolean) => {
    const toast = document.querySelector("#toast")
    if (!toast) return

    toast.innerHTML = message
    if (isError) toast.classList.add("error")
    else toast.classList.remove("error")

    toast.classList.add("show")
    setTimeout(() => {
        toast.classList.remove("show")
    }, 3000)
}


const sumGP = (a: number, n: number) => a * (1 - Math.pow(a, n)) / (1 - a)

export const getBuyPrice = (price: number, n: number) =>
    price * sumGP(1.001, n);

export const getSellPrice = (price: number, n: number) =>
    price * sumGP(1/1.001, n);