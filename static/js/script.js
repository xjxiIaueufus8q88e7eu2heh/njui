document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('download-form');
    const progressSection = document.getElementById('progress-section');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const statusMessage = document.getElementById('status-message');
    const resultSection = document.getElementById('result-section');
    const downloadBtn = document.getElementById('download-btn');
    const newDownloadBtn = document.getElementById('new-download-btn');
    const flashContainer = document.getElementById('flash-messages');
    const videoPlayer = document.getElementById('preview-player');
    const previewPlaceholder = document.getElementById('preview-placeholder');
    const videoLoading = document.getElementById('video-loading');
    const particlesContainer = document.getElementById('particles');
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('i');
    
    // ===== Counter Animation =====
    function animateCounter(element, target, suffix = '', precision = 0) {
        let start = 0;
        const duration = 2000;
        const startTime = performance.now();
        const isInteger = Number.isInteger(target);
        
        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const value = progress * target;
            
            element.textContent = isInteger ? 
                Math.floor(value) + suffix : 
                value.toFixed(precision) + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }
        requestAnimationFrame(updateCounter);
    }
    
    // Initialize counters
    animateCounter(document.getElementById('avg-processing'), 4.8, '', 1);
    animateCounter(document.getElementById('clips-created'), 12000, '', 0);
    animateCounter(document.getElementById('success-rate'), 99.7, '', 1);
    
    // ===== Theme Management =====
    // Set default to dark mode
    document.body.classList.add('dark-mode');
    document.body.classList.remove('light-mode');
    themeIcon.className = 'fas fa-sun';
    localStorage.setItem('preferredTheme', 'dark');
    
    // Toggle theme manually
    themeToggle.addEventListener('click', function() {
        const isDarkMode = document.body.classList.contains('dark-mode');
        
        document.body.classList.toggle('dark-mode', !isDarkMode);
        document.body.classList.toggle('light-mode', isDarkMode);
        themeIcon.className = isDarkMode ? 'fas fa-moon' : 'fas fa-sun';
        
        // Save preference
        localStorage.setItem('preferredTheme', isDarkMode ? 'light' : 'dark');
        
        // Animation
        this.classList.add('animate__animated', 'animate__rubberBand');
        setTimeout(() => {
            this.classList.remove('animate__animated', 'animate__rubberBand');
        }, 1000);
    });
    
    // ===== Enhanced Particle System =====
    function createParticles() {
        const particleCount = 100;
        const sizes = ['small', 'medium', 'large', 'x-large'];
        const colors = [
            'linear-gradient(135deg, #8a2be2, #4361ee)',
            'linear-gradient(135deg, #4cc9f0, #38b000)',
            'linear-gradient(135deg, #9d4edd, #f72585)',
            'linear-gradient(135deg, #7209b7, #3a0ca3)'
        ];
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.classList.add('particle');
            
            // Random size
            const size = sizes[Math.floor(Math.random() * sizes.length)];
            particle.classList.add(size);
            
            // Random position
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            
            // Random color
            const color = colors[Math.floor(Math.random() * colors.length)];
            particle.style.background = color;
            
            // Random animation
            const duration = Math.random() * 30 + 10;
            const delay = Math.random() * 5;
            particle.style.animationDuration = `${duration}s`;
            particle.style.animationDelay = `${delay}s`;
            
            particlesContainer.appendChild(particle);
        }
    }
    
    // ===== Button Effects =====
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        // Ripple effect
        button.addEventListener('click', function(e) {
            const x = e.clientX - e.target.getBoundingClientRect().left;
            const y = e.clientY - e.target.getBoundingClientRect().top;
            
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        // 3D tilt effect
        button.addEventListener('mousemove', (e) => {
            const rect = button.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            
            const tiltX = (x - 0.5) * 20;
            const tiltY = (y - 0.5) * 20;
            
            button.style.transform = `translateY(-3px) rotateX(${-tiltY}deg) rotateY(${tiltX}deg) scale(1.05)`;
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = '';
        });
    });
    
    // ===== Form Animations =====
    const formInputs = document.querySelectorAll('.form-control');
    formInputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.style.transform = 'translateY(-5px)';
        });
        
        input.addEventListener('blur', () => {
            input.parentElement.style.transform = '';
        });
    });
    
    // ===== Video Player =====
    videoPlayer.preload = 'none';
    videoPlayer.playsInline = true;
    videoPlayer.disableRemotePlayback = true;
    videoPlayer.crossOrigin = 'anonymous';
    
    // ===== Form Submission =====
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(form);
        const data = {
            link: formData.get('link'),
            ss: formData.get('ss'),
            to: formData.get('to'),
            output: formData.get('output')
        };
        
        // Show progress section with animation
        progressSection.style.display = 'block';
        resultSection.style.display = 'none';
        progressSection.style.animation = 'fadeIn 0.6s ease-out';
        
        // Scroll to progress
        progressSection.scrollIntoView({ behavior: 'smooth' });
        
        // Simulate progress for demo
        if (data.link.includes('demo')) {
            simulateDemoProgress(data);
            return;
        }
        
        try {
            // Start download process
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            // Handle error responses
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.errors.join(', '));
            }
            
            // Process successful response
            const result = await response.json();
            trackProgress(result.request_id, result.filename);
        } catch (error) {
            showFlash('error', error.message);
            statusMessage.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${error.message}`;
            newDownloadBtn.style.display = 'block';
        }
    });
    
    // ===== Video Preview =====
    previewPlaceholder.addEventListener('click', async function() {
        if (videoPlayer.src) {
            try {
                // Show loading indicator with animation
                videoLoading.style.display = 'flex';
                videoLoading.style.animation = 'fadeIn 0.3s ease-out';
                
                // Preload first 5MB before showing player
                await preloadVideo(videoPlayer.src);
                
                // Hide placeholder and show player with animation
                previewPlaceholder.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    previewPlaceholder.style.display = 'none';
                    videoPlayer.style.display = 'block';
                    videoPlayer.style.animation = 'fadeIn 0.6s ease-out';
                    videoLoading.style.display = 'none';
                    
                    // Start playback
                    const playPromise = videoPlayer.play();
                    
                    if (playPromise !== undefined) {
                        playPromise.catch(e => {
                            showFlash('info', 'Click the play button to start video');
                        });
                    }
                }, 300);
            } catch (e) {
                console.error('Preload failed:', e);
                videoLoading.style.display = 'none';
                showFlash('error', 'Failed to load video preview');
            }
        }
    });
    
    // ===== Helper Functions =====
    async function preloadVideo(url) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', url);
            xhr.setRequestHeader('Range', 'bytes=0-5242880'); // Preload first 5MB
            
            xhr.onload = function() {
                if (xhr.status === 206) {
                    resolve();
                } else {
                    reject(new Error('Preload failed'));
                }
            };
            
            xhr.onerror = function() {
                reject(new Error('Preload failed'));
            };
            
            xhr.send();
        });
    }
    
    function simulateDemoProgress(data) {
        let progress = 0;
        const messages = [
            "Connecting to YouTube...",
            "Analyzing video content...",
            "Extracting HD streams...",
            "Processing clip segment...",
            "Finalizing your video..."
        ];
        
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 8) + 3;
            if (progress > 100) progress = 100;
            
            progressFill.style.width = `${progress}%`;
            progressPercent.textContent = `${progress}%`;
            
            // Add pulse effect when progress updates
            progressFill.style.animation = 'none';
            void progressFill.offsetWidth; // Trigger reflow
            progressFill.style.animation = 'pulse 0.5s ease';
            
            // Update message every 20% progress
            if (progress <= 20) {
                statusMessage.textContent = messages[0];
            } else if (progress <= 40) {
                statusMessage.textContent = messages[1];
            } else if (progress <= 60) {
                statusMessage.textContent = messages[2];
            } else if (progress <= 80) {
                statusMessage.textContent = messages[3];
            } else {
                statusMessage.textContent = messages[4];
            }
            
            if (progress === 100) {
                clearInterval(interval);
                setTimeout(() => {
                    // Hide progress and show result with animation
                    progressSection.style.animation = 'fadeOut 0.4s ease-out';
                    setTimeout(() => {
                        progressSection.style.display = 'none';
                        resultSection.style.display = 'block';
                        resultSection.style.animation = 'zoomIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                        
                        // Show preview player with animation
                        previewPlaceholder.style.animation = 'fadeOut 0.3s ease-out';
                        setTimeout(() => {
                            previewPlaceholder.style.display = 'none';
                            videoPlayer.style.display = 'block';
                            videoPlayer.style.animation = 'fadeIn 0.6s ease-out';
                            
                            // Set a demo video source
                            videoPlayer.src = "https://assets.codepen.io/4175254/stock-video.mp4";
                            
                            // Set up download button
                            downloadBtn.onclick = () => {
                                const link = document.createElement('a');
                                link.href = videoPlayer.src;
                                link.download = data.output || 'your_clip.mp4';
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                            };
                            
                            // Scroll to result
                            resultSection.scrollIntoView({ behavior: 'smooth' });
                        }, 300);
                    }, 400);
                }, 800);
            }
        }, 200);
    }
    
    function trackProgress(requestId, filename) {
        let progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/progress/${requestId}`);
                const data = await response.json();
                
                // Update progress with animation
                const progress = data.progress || 0;
                progressFill.style.width = `${progress}%`;
                progressPercent.textContent = `${Math.round(progress)}%`;
                statusMessage.innerHTML = `<i class="fas fa-info-circle"></i> ${data.message}`;
                
                // Add pulse effect when progress updates
                if (progress > 0) {
                    progressFill.style.animation = 'none';
                    void progressFill.offsetWidth; // Trigger reflow
                    progressFill.style.animation = 'pulse 0.5s ease';
                }
                
                // Handle different states
                if (data.status === 'completed') {
                    clearInterval(progressInterval);
                    
                    // Hide progress and show result with animation
                    progressSection.style.animation = 'fadeOut 0.4s ease-out';
                    setTimeout(() => {
                        progressSection.style.display = 'none';
                        resultSection.style.display = 'block';
                        resultSection.style.animation = 'zoomIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                        
                        // Set the video source
                        videoPlayer.src = `/stream/${filename}`;
                        
                        // Set up download button
                        downloadBtn.onclick = () => {
                            window.location.href = `/download/${filename}`;
                            
                            // Cleanup after 1 hour
                            setTimeout(() => {
                                fetch(`/cleanup/${filename}`);
                            }, 3600000);
                        };
                        
                        // Scroll to result
                        resultSection.scrollIntoView({ behavior: 'smooth' });
                    }, 400);
                } 
                else if (data.status === 'error') {
                    clearInterval(progressInterval);
                    statusMessage.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error: ${data.message}`;
                }
            } catch (error) {
                clearInterval(progressInterval);
                statusMessage.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error tracking progress: ${error.message}`;
            }
        }, 1000);
    }
    
    function showFlash(type, message) {
        const flash = document.createElement('div');
        flash.className = `alert ${type}`;
        flash.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
            ${message}
        `;
        
        flashContainer.appendChild(flash);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            flash.style.animation = 'slideOut 0.4s forwards';
            setTimeout(() => {
                flash.remove();
            }, 400);
        }, 5000);
    }
    
    // ===== Initialize =====
    createParticles();
    
    // Setup new download button
    newDownloadBtn.onclick = () => {
        progressSection.style.animation = 'fadeOut 0.4s ease-out';
        resultSection.style.animation = 'fadeOut 0.4s ease-out';
        setTimeout(() => {
            progressSection.style.display = 'none';
            resultSection.style.display = 'none';
            form.reset();
            
            // Reset preview with animation
            videoPlayer.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                videoPlayer.style.display = 'none';
                videoPlayer.src = '';
                previewPlaceholder.style.display = 'flex';
                previewPlaceholder.style.animation = 'fadeIn 0.6s ease-out';
            }, 300);
        }, 400);
    };
    
    // Initialize animations on elements when they come into view
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('.card, .stat-card, .form-group').forEach(el => {
        observer.observe(el);
    });
});