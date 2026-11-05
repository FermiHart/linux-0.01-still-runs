#ifndef _STRING_H_
#define _STRING_H_

#ifndef NULL
#define NULL ((void *) 0)
#endif

#ifndef _SIZE_T
#define _SIZE_T
typedef unsigned int size_t;
#endif

extern char * strerror(int errno);

extern inline char * strcpy(char * dest,const char * src)
{
	char * ret=dest;

	while ((*dest++=*src++))
		;
	return ret;
}

extern inline char * strncpy(char * dest,const char * src,int count)
{
	char * ret=dest;

	while (count>0 && *src) {
		*dest++=*src++;
		count--;
	}
	while (count-- > 0)
		*dest++=0;
	return ret;
}

extern inline char * strcat(char * dest,const char * src)
{
	char * ret=dest;

	while (*dest)
		dest++;
	while ((*dest++=*src++))
		;
	return ret;
}

extern inline char * strncat(char * dest,const char * src,int count)
{
	char * ret=dest;

	while (*dest)
		dest++;
	while (count-- > 0 && *src)
		*dest++=*src++;
	*dest=0;
	return ret;
}

extern inline int strcmp(const char * cs,const char * ct)
{
	while (*cs && *cs == *ct) {
		cs++;
		ct++;
	}
	return (int)(unsigned char)*cs-(int)(unsigned char)*ct;
}

extern inline int strncmp(const char * cs,const char * ct,int count)
{
	while (count-- > 0) {
		if (*cs != *ct)
			return (int)(unsigned char)*cs-(int)(unsigned char)*ct;
		if (!*cs)
			return 0;
		cs++;
		ct++;
	}
	return 0;
}

extern inline char * strchr(const char * s,char c)
{
	do {
		if (*s == c)
			return (char *)s;
	} while (*s++);
	return NULL;
}

extern inline char * strrchr(const char * s,char c)
{
	const char * ret=NULL;

	do {
		if (*s == c)
			ret=s;
	} while (*s++);
	return (char *)ret;
}

extern inline int strspn(const char * cs,const char * ct)
{
	const char * start=cs;
	const char * p;

	while (*cs) {
		for (p=ct ; *p && *p != *cs ; p++)
			;
		if (!*p)
			break;
		cs++;
	}
	return cs-start;
}

extern inline int strcspn(const char * cs,const char * ct)
{
	const char * start=cs;
	const char * p;

	while (*cs) {
		for (p=ct ; *p && *p != *cs ; p++)
			;
		if (*p)
			break;
		cs++;
	}
	return cs-start;
}

extern inline char * strpbrk(const char * cs,const char * ct)
{
	const char * p;

	while (*cs) {
		for (p=ct ; *p ; p++)
			if (*p == *cs)
				return (char *)cs;
		cs++;
	}
	return NULL;
}

extern inline char * strstr(const char * cs,const char * ct)
{
	const char * a,*b;

	if (!*ct)
		return (char *)cs;
	while (*cs) {
		a=cs;
		b=ct;
		while (*a && *b && *a == *b) {
			a++;
			b++;
		}
		if (!*b)
			return (char *)cs;
		cs++;
	}
	return NULL;
}

extern inline int strlen(const char * s)
{
	const char * start=s;

	while (*s)
		s++;
	return s-start;
}

extern char * ___strtok;

extern inline char * strtok(char * s,const char * ct)
{
	char * token;

	if (!s)
		s=___strtok;
	if (!s)
		return NULL;
	while (*s && strchr(ct,*s))
		s++;
	if (!*s) {
		___strtok=NULL;
		return NULL;
	}
	token=s;
	while (*s && !strchr(ct,*s))
		s++;
	if (*s) {
		*s++=0;
		___strtok=s;
	} else
		___strtok=NULL;
	return token;
}

extern inline void * memcpy(void * dest,const void * src,int n)
{
	char * d=dest;
	const char * s=src;
	void * ret=dest;

	while (n-- > 0)
		*d++=*s++;
	return ret;
}

extern inline void * memmove(void * dest,const void * src,int n)
{
	char * d=dest;
	const char * s=src;
	void * ret=dest;

	if (n <= 0)
		return ret;
	if (d < s) {
		while (n-- > 0)
			*d++=*s++;
	} else if (d > s) {
		d += n;
		s += n;
		while (n-- > 0)
			*--d=*--s;
	}
	return ret;
}

extern inline int memcmp(const void * cs,const void * ct,int count)
{
	const unsigned char * a=cs;
	const unsigned char * b=ct;

	while (count-- > 0) {
		if (*a != *b)
			return (int)*a-(int)*b;
		a++;
		b++;
	}
	return 0;
}

extern inline void * memchr(const void * cs,char c,int count)
{
	const unsigned char * p=cs;
	unsigned char ch=c;

	while (count-- > 0) {
		if (*p == ch)
			return (void *)p;
		p++;
	}
	return NULL;
}

extern inline void * memset(void * s,char c,int count)
{
	unsigned char * p=s;
	void * ret=s;

	while (count-- > 0)
		*p++=(unsigned char)c;
	return ret;
}

#endif
